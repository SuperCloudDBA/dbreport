# -*- coding: utf-8 -*-
"""
输出目标 PostgreSQL 数据库库表信息
"""
# Build-in Modules
import json
import datetime
import decimal
import time

# 3rd-part Modules
import psycopg2
import argparse
from jinja2 import Template
from aliyun_get_pg_healthcheck_outhtml import GetReport
# 渲染的json文件名
JSON_FILENAME='data.json'

class CJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(obj, decimal.Decimal):
            return str(obj)
        else:
            return json.JSONEncoder.default(self, obj)


class PGHelper:
    def __init__(self, **kwargs):
        self.url = kwargs['url']
        self.port = int(kwargs['port'])
        self.username = kwargs['username']
        self.password = kwargs['password']
        self.dbname = kwargs['dbname']
        self.charset = "utf8"
        try:
            self.conn = psycopg2.connect(database=self.dbname, user=self.username, password=self.password, host=self.url, port=self.port)
            # conn = psycopg2.connect(database="postgres", user="ccmonitor",
            #                         password="bqEjsAFNH3pQXb2kG55zAaa",
            #                         host="pgm-bp1jz47p162k76xb9o.pg.rds.aliyuncs.com", port="1921"
            self.cur = self.conn.cursor()
        except Exception as e:
            print(str(e))
            self.error = 1
        else:
            self.error = 0

    def col_query(self, sql):
        """
        打印表的列名
        :return list
        """
        self.cur.execute(sql)
        return self.cur.fetchall()

    def commit(self):
        self.conn.commit()

    def close(self):
        self.cur.close()
        self.conn.close()


class GetInfo:
    """
    获取报告需要的后端逻辑
    """

    def __init__(self):
        """
        数据库后端逻辑
        """
        connnections = '''select max_conn 最大连接数, now_conn 当前连接数, max_conn-now_conn 剩余连接数 from (select setting::int8 as max_conn,(select count(*) from pg_stat_activity) as now_conn from pg_settings where name = 'max_connections') t;'''
        age_large = ''' select
        datname, age(datfrozenxid) as age
        from pg_database where
        age(datfrozenxid) > 1000000000
        order
        by
        2
        desc;'''
        select_age = '''select relname,age(relfrozenxid) as age,pg_relation_size(oid)/1024/1024/1024.0 table_size from pg_class where relkind='r' and age(relfrozenxid)>800000000 and pg_relation_size(oid)/1024/1024/1024.0 > 10 order by 3 desc;'''
        index_large = '''select t2.nspname, t1.relname, t3.idx_cnt from pg_class t1, pg_namespace t2, (select indrelid,count(*) idx_cnt from pg_index group by 1 having count(*)>4) t3 where t1.oid=t3.indrelid and t1.relnamespace=t2.oid and pg_relation_size(t1.oid)/1024/1024.0>10 order by t3.idx_cnt desc;'''
        unuse_index = '''select t2.schemaname,t2.relname,t2.indexrelname,t2.idx_scan,t2.idx_tup_read,t2.idx_tup_fetch,pg_relation_size(indexrelid) as pg_relation_size from pg_stat_all_tables t1,pg_stat_all_indexes t2 where t1.relid=t2.relid and t2.idx_scan<1000 and t2.schemaname not in ('pg_toast','pg_catalog') and indexrelid not in (select conindid from pg_constraint where contype in ('p','u')) and pg_relation_size(indexrelid)>6553600 order by pg_relation_size(indexrelid) desc;'''
        partition_table = '''SELECT
    nspname ,
    relname ,
    COUNT(*) AS partition_num
FROM
    pg_class c ,
    pg_namespace n ,
    pg_inherits i
WHERE
    c.oid = i.inhparent
    AND c.relnamespace = n.oid
    AND c.relhassubclass
    AND c.relkind = 'r'
GROUP BY 1,2  ORDER BY partition_num DESC;'''
        expand = '''select * from 
(
SELECT
  current_database() AS db, schemaname, tablename, reltuples::bigint AS tups, relpages::bigint AS pages, otta,
  ROUND(CASE WHEN otta=0 OR sml.relpages=0 OR sml.relpages=otta THEN 0.0 ELSE sml.relpages/otta::numeric END,1) AS tbloat,
  CASE WHEN relpages < otta THEN 0 ELSE relpages::bigint - otta END AS wastedpages,
  CASE WHEN relpages < otta THEN 0 ELSE bs*(sml.relpages-otta)::bigint END AS wastedbytes,
  CASE WHEN relpages < otta THEN '0 bytes'::text ELSE (bs*(relpages-otta))::bigint || ' bytes' END AS wastedsize,
  iname, ituples::bigint AS itups, ipages::bigint AS ipages, iotta,
  ROUND(CASE WHEN iotta=0 OR ipages=0 OR ipages=iotta THEN 0.0 ELSE ipages/iotta::numeric END,1) AS ibloat,
  CASE WHEN ipages < iotta THEN 0 ELSE ipages::bigint - iotta END AS wastedipages,
  CASE WHEN ipages < iotta THEN 0 ELSE bs*(ipages-iotta) END AS wastedibytes,
  CASE WHEN ipages < iotta THEN '0 bytes' ELSE (bs*(ipages-iotta))::bigint || ' bytes' END AS wastedisize,
  CASE WHEN relpages < otta THEN
    CASE WHEN ipages < iotta THEN 0 ELSE bs*(ipages-iotta::bigint) END
    ELSE CASE WHEN ipages < iotta THEN bs*(relpages-otta::bigint)
      ELSE bs*(relpages-otta::bigint + ipages-iotta::bigint) END
  END AS totalwastedbytes
FROM (
  SELECT
    nn.nspname AS schemaname,
    cc.relname AS tablename,
    COALESCE(cc.reltuples,0) AS reltuples,
    COALESCE(cc.relpages,0) AS relpages,
    COALESCE(bs,0) AS bs,
    COALESCE(CEIL((cc.reltuples*((datahdr+ma-
      (CASE WHEN datahdr%ma=0 THEN ma ELSE datahdr%ma END))+nullhdr2+4))/(bs-20::float)),0) AS otta,
    COALESCE(c2.relname,'?') AS iname, COALESCE(c2.reltuples,0) AS ituples, COALESCE(c2.relpages,0) AS ipages,
    COALESCE(CEIL((c2.reltuples*(datahdr-12))/(bs-20::float)),0) AS iotta -- very rough approximation, assumes all cols
  FROM
     pg_class cc
  JOIN pg_namespace nn ON cc.relnamespace = nn.oid AND nn.nspname <> 'information_schema'
  LEFT JOIN
  (
    SELECT
      ma,bs,foo.nspname,foo.relname,
      (datawidth+(hdr+ma-(case when hdr%ma=0 THEN ma ELSE hdr%ma END)))::numeric AS datahdr,
      (maxfracsum*(nullhdr+ma-(case when nullhdr%ma=0 THEN ma ELSE nullhdr%ma END))) AS nullhdr2
    FROM (
      SELECT
        ns.nspname, tbl.relname, hdr, ma, bs,
        SUM((1-coalesce(null_frac,0))*coalesce(avg_width, 2048)) AS datawidth,
        MAX(coalesce(null_frac,0)) AS maxfracsum,
        hdr+(
          SELECT 1+count(*)/8
          FROM pg_stats s2
          WHERE null_frac<>0 AND s2.schemaname = ns.nspname AND s2.tablename = tbl.relname
        ) AS nullhdr
      FROM pg_attribute att 
      JOIN pg_class tbl ON att.attrelid = tbl.oid
      JOIN pg_namespace ns ON ns.oid = tbl.relnamespace 
      LEFT JOIN pg_stats s ON s.schemaname=ns.nspname
      AND s.tablename = tbl.relname
      AND s.inherited=false
      AND s.attname=att.attname,
      (
        SELECT
          (SELECT current_setting('block_size')::numeric) AS bs,
            CASE WHEN SUBSTRING(SPLIT_PART(v, ' ', 2) FROM '#"[0-9]+.[0-9]+#"%' for '#')
              IN ('8.0','8.1','8.2') THEN 27 ELSE 23 END AS hdr,
          CASE WHEN v ~ 'mingw32' OR v ~ '64-bit' THEN 8 ELSE 4 END AS ma
        FROM (SELECT version() AS v) AS foo
      ) AS constants
      WHERE att.attnum > 0 AND tbl.relkind='r'
      GROUP BY 1,2,3,4,5
    ) AS foo
  ) AS rs
  ON cc.relname = rs.relname AND nn.nspname = rs.nspname
  LEFT JOIN pg_index i ON indrelid = cc.oid
  LEFT JOIN pg_class c2 ON c2.oid = i.indexrelid
) AS sml ORDER BY totalwastedbytes DESC
) t where totalwastedbytes/1024/1024 > 1024;'''
        refuse = '''select schemaname,relname,n_live_tup,n_dead_tup from pg_stat_all_tables where n_live_tup>0 and n_dead_tup/n_live_tup>0.2 and schemaname not in ('pg_toast','pg_catalog') and n_live_tup>100000 or n_dead_tup>100000;'''

        self.sql_params = {
            'postgresql'.lower(): [
                {
                    'type': 'connnections',
                    'query': connnections,
                    'desc': "连接数",
                    'fields': ["最大连接数", "当前连接数", "剩余连接数"]
                },
                {
                    'type': 'age_large',
                    'query': age_large,
                    'desc': "年龄大于10亿的数据库",
                    'fields': ["datname", "age"]
                },
                {
                    'type': 'select_age',
                    'query': select_age,
                    'desc': "查询大于10GB以及年龄大于9亿的表",
                    'fields': ["relname", "age", "table_size"]
                },
                {
                    'type': 'index_large',
                    'query': index_large,
                    'desc': "查询索引数超过4并且SIZE大于10MB的表",
                    'fields': ["nspname", "relname", "idx_cnt"]
                },
                {
                    'type': 'unuse_index',
                    'query': unuse_index,
                    'desc': "上次巡检以来未使用或使用较少的索引  ",
                    'fields': ["schemaname", "relname", "idx_scan","idx_tup_read","idx_tup_fetch","pg_relation_size"]
                },
                {
                    'type': 'partition_table',
                    'query': partition_table,
                    'desc': "分区表检查",
                    'fields': ["nspname", "relname", "partition_num"]
                },
                {
                    'type': 'expand',
                    'query': expand,
                    'desc': "膨胀检查",
                    'fields': ["db", "schemaname", "tablename", "tups", "pages", "otta", "tbloat", "wastepages", "wastedbytes", "wastedsize", "iname", "itups", "ipages", "iotta", "ibloat", "wastedipages", "wastedibytes", "wastedisize", "totalwastedbytes"]
                },
                {
                    'type': 'refuse',
                    'query': refuse,
                    'desc': "检查垃圾数据",
                    'fields': ["schemaname", "relname", "n_live_tup","n_dead_tup"]
                }

            ],
            # 'sqlserver': [{}],
            # 'postgresql': [{}],
            # 'oracle': [{}],
        }

    def get_info(self, engine, filter_infos):
        """
        根据指定的数据库类型 和 报告内容 进行过滤，返回过滤后的SQL
        """
        return list(filter(lambda x: x['type'] in filter_infos, self.sql_params[engine]))

class GetJson:
    """
    渲染数据库报告结果到Json文件
    """

    def __init__(self, **kwargs):
        self.data = kwargs
        self.jsontempdata = json.dumps(self.data, cls=CJsonEncoder, ensure_ascii=False, indent=2)

    def maker(self, out_dir):
        file_name = JSON_FILENAME
        with open('{}/{}'.format(out_dir, file_name), 'w', encoding='utf-8') as f:
            f.write(self.jsontempdata)

def starup(**kwargs):
    params = {
        'url': kwargs['host'],
        'port': kwargs['port'],
        'username': kwargs['user'],
        'password': kwargs['password'],
        'dbname': kwargs['dbname'],
    }
    # 1.根据传递的参数对报告后端逻辑进行过滤
    info_api = GetInfo()
    sql_list = info_api.get_info(kwargs['engine'], kwargs["info"])
    # print(json.dumps(sql_list, indent=2, ensure_ascii=False))

    # 2.获取待渲染的报告数据
    sql_api = PGHelper(**params)
    data = []
    for sql in sql_list:
        sql_results = sql_api.col_query(sql["query"])
        #sql["sql_result"] = sql_results
        datajsons=[]
        for sql_result in sql_results:
            datajson=dict(zip(sql["fields"],sql_result))
            datajsons.append(datajson)
        sql["rows"]=json.loads(json.dumps(datajsons, cls=CJsonEncoder, ensure_ascii=False))
        data.append(sql)
    #print(json.dumps(data, cls=CJsonEncoder, ensure_ascii=False, indent=2))

    # 3.输出json文件
    temp_data = {
        'data': data,
        'json_file': JSON_FILENAME
    }
    #jsontempdata = json.dumps(temp_data, cls=CJsonEncoder, ensure_ascii=False, indent=2)
    #report = GetJson(jsontempdata)
    #jsonfile = GetJson(**temp_data)
    #jsonfile.maker(kwargs['out_dir'])

    # 4. 渲染报告
    report = GetReport(**temp_data)
    report.maker(kwargs['host'],kwargs['out_dir'])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='''PostgreSQL 库表统计报告小工具
关于数据库的整体库表空间使用情况	
1. 库空间统计
2. 表空间统计
Example：
    python3 aliyun_get_pg_healthcheck.py --Engine ENGINE --Host HOST --Port PORT --User USER --Password PASSWORD --DBName DBNAME --Info INFO 

''', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--Engine", help='''Engine 必要参数
    只能选择一种类型 支持的所有类型：PostgreSQL 不区分大小写''')
    parser.add_argument("--Host", help="Host 必要参数")
    parser.add_argument("--Port", help="Port 必要参数")
    parser.add_argument("--User", help="User 必要参数")
    parser.add_argument("--Password", help="Password 必要参数")
    parser.add_argument("--DBName", help="DBName 必要参数")
    parser.add_argument("--Info", default='all',
                        help='''Info 非必要参数，默认all，也可单独指定例如 db_size 或 db_size,table_size; 多个使用逗号分割 db_size:获取mssql表空间统计 table_size:获取mssql表空间统计''')
    parser.add_argument("--OutDir", help="输出目录 必要参数 需要提前创建该目录")

    args = parser.parse_args()
    if args.Info == 'all':
        info = ['connnections','age_large','select_age','index_large','unuse_index','partition_table', 'expand','refuse']
    elif len(args.Info.split(',')):
        info = args.Info.split(',')
    params = {
        'info': info,
        'engine': args.Engine.lower(),
        'host': args.Host,
        'port': args.Port,
        'user': args.User,
        'password': args.Password,
        'dbname': args.DBName,
        'out_dir': args.OutDir,
    }

    if args.Engine.lower() == 'postgresql'.lower():
        starup(**params)
    else:
        print('请选择 PostgreSQL 类型的数据库。')