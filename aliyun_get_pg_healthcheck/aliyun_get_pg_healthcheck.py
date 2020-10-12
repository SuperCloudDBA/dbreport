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
        #数据库
        dtname = '''select datname from pg_database where datname not in ($$template0$$, $$template1$$)'''
        #连接数
        connnections = '''select max_conn 最大连接数, now_conn 当前连接数, max_conn-now_conn 剩余连接数 from (select setting::int8 as max_conn,(select count(*) from pg_stat_activity) as now_conn from pg_settings where name = 'max_connections') t;'''
        #数据年龄
        data_age = ''' select datname, age(datfrozenxid) as age from pg_database order by 2 desc;'''
        #年龄大于N的对象占用空间数，年龄大于12亿的数据库，占用的空间数
        data_size = '''select COALESCE(pg_size_pretty(sum(pg_database_size(oid))),'') as pg_size_pretty from pg_database where age(datfrozenxid)>1200000000;'''
        #表膨胀
        surface_expansion = '''SELECT  
  current_database() AS db, schemaname, tablename, reltuples::bigint AS tups, relpages::bigint AS pages, otta,  
  ROUND(CASE WHEN otta=0 OR sml.relpages=0 OR sml.relpages=otta THEN 0.0 ELSE sml.relpages/otta::numeric END,1) AS tbloat,  
  CASE WHEN relpages < otta THEN 0 ELSE relpages::bigint - otta END AS wastedpages,  
  CASE WHEN relpages < otta THEN 0 ELSE bs*(sml.relpages-otta)::bigint END AS wastedbytes,  
  CASE WHEN relpages < otta THEN $$0 bytes$$::text ELSE (bs*(relpages-otta))::bigint || $$ bytes$$ END AS wastedsize,  
  iname, ituples::bigint AS itups, ipages::bigint AS ipages, iotta,  
  ROUND(CASE WHEN iotta=0 OR ipages=0 OR ipages=iotta THEN 0.0 ELSE ipages/iotta::numeric END,1) AS ibloat,  
  CASE WHEN ipages < iotta THEN 0 ELSE ipages::bigint - iotta END AS wastedipages,  
  CASE WHEN ipages < iotta THEN 0 ELSE bs*(ipages-iotta) END AS wastedibytes,  
  CASE WHEN ipages < iotta THEN $$0 bytes$$ ELSE (bs*(ipages-iotta))::bigint || $$ bytes$$ END AS wastedisize,  
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
    COALESCE(c2.relname,$$?$$) AS iname, COALESCE(c2.reltuples,0) AS ituples, COALESCE(c2.relpages,0) AS ipages,  
    COALESCE(CEIL((c2.reltuples*(datahdr-12))/(bs-20::float)),0) AS iotta -- very rough approximation, assumes all cols  
  FROM  
     pg_class cc  
  JOIN pg_namespace nn ON cc.relnamespace = nn.oid AND nn.nspname <> $$information_schema$$  
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
          (SELECT current_setting($$block_size$$)::numeric) AS bs,  
            CASE WHEN SUBSTRING(SPLIT_PART(v, $$ $$, 2) FROM $$#"[0-9]+.[0-9]+#"%$$ for $$#$$)  
              IN ($$8.0$$,$$8.1$$,$$8.2$$) THEN 27 ELSE 23 END AS hdr,  
          CASE WHEN v ~ $$mingw32$$ OR v ~ $$64-bit$$ THEN 8 ELSE 4 END AS ma  
        FROM (SELECT version() AS v) AS foo  
      ) AS constants  
      WHERE att.attnum > 0 AND tbl.relkind=$$r$$  
      GROUP BY 1,2,3,4,5  
    ) AS foo  
  ) AS rs  
  ON cc.relname = rs.relname AND nn.nspname = rs.nspname  
  LEFT JOIN pg_index i ON indrelid = cc.oid  
  LEFT JOIN pg_class c2 ON c2.oid = i.indexrelid  
) AS sml order by wastedbytes desc limit 5'''
        #索引膨胀
        index_inflation = '''SELECT  
  current_database() AS db, schemaname, tablename, reltuples::bigint AS tups, relpages::bigint AS pages, otta,  
  ROUND(CASE WHEN otta=0 OR sml.relpages=0 OR sml.relpages=otta THEN 0.0 ELSE sml.relpages/otta::numeric END,1) AS tbloat,  
  CASE WHEN relpages < otta THEN 0 ELSE relpages::bigint - otta END AS wastedpages,  
  CASE WHEN relpages < otta THEN 0 ELSE bs*(sml.relpages-otta)::bigint END AS wastedbytes,  
  CASE WHEN relpages < otta THEN $$0 bytes$$::text ELSE (bs*(relpages-otta))::bigint || $$ bytes$$ END AS wastedsize,  
  iname, ituples::bigint AS itups, ipages::bigint AS ipages, iotta,  
  ROUND(CASE WHEN iotta=0 OR ipages=0 OR ipages=iotta THEN 0.0 ELSE ipages/iotta::numeric END,1) AS ibloat,  
  CASE WHEN ipages < iotta THEN 0 ELSE ipages::bigint - iotta END AS wastedipages,  
  CASE WHEN ipages < iotta THEN 0 ELSE bs*(ipages-iotta) END AS wastedibytes,  
  CASE WHEN ipages < iotta THEN $$0 bytes$$ ELSE (bs*(ipages-iotta))::bigint || $$ bytes$$ END AS wastedisize,  
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
    COALESCE(c2.relname,$$?$$) AS iname, COALESCE(c2.reltuples,0) AS ituples, COALESCE(c2.relpages,0) AS ipages,  
    COALESCE(CEIL((c2.reltuples*(datahdr-12))/(bs-20::float)),0) AS iotta -- very rough approximation, assumes all cols  
  FROM  
     pg_class cc  
  JOIN pg_namespace nn ON cc.relnamespace = nn.oid AND nn.nspname <> $$information_schema$$  
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
          (SELECT current_setting($$block_size$$)::numeric) AS bs,  
            CASE WHEN SUBSTRING(SPLIT_PART(v, $$ $$, 2) FROM $$#"[0-9]+.[0-9]+#"%$$ for $$#$$)  
              IN ($$8.0$$,$$8.1$$,$$8.2$$) THEN 27 ELSE 23 END AS hdr,  
          CASE WHEN v ~ $$mingw32$$ OR v ~ $$64-bit$$ THEN 8 ELSE 4 END AS ma  
        FROM (SELECT version() AS v) AS foo  
      ) AS constants  
      WHERE att.attnum > 0 AND tbl.relkind=$$r$$  
      GROUP BY 1,2,3,4,5  
    ) AS foo  
  ) AS rs  
  ON cc.relname = rs.relname AND nn.nspname = rs.nspname  
  LEFT JOIN pg_index i ON indrelid = cc.oid  
  LEFT JOIN pg_class c2 ON c2.oid = i.indexrelid  
) AS sml order by wastedibytes desc limit 5'''
        #未使用索引
        unused_index = '''select current_database(),relid, indexrelid, schemaname, relname, indexrelname, idx_scan,
                               idx_tup_read, idx_tup_fetch from pg_stat_all_indexes where idx_scan=0 or idx_tup_read=0 or idx_tup_fetch=0;'''
        #未使用查询表
        unused_query_table = '''select current_database(),relid,schemaname,relname,seq_scan,seq_tup_read,COALESCE(idx_scan,0) as idx_scan from pg_stat_all_tables where seq_scan=0 and idx_scan=0;'''
        #热表
        hot_table = '''select current_database(),relid,schemaname,relname,seq_scan,seq_tup_read,COALESCE(idx_scan,0) as idx_scan from pg_stat_all_tables order by seq_scan+idx_scan desc limit 10;'''
        #冷表
        cold_table = '''select current_database(),relid,schemaname,relname,seq_scan,seq_tup_read,COALESCE(idx_scan,0) as idx_scan from pg_stat_all_tables order by seq_scan+idx_scan limit 10;'''
        #热索引
        hot_index = '''select current_database(),current_database(),relid, indexrelid, schemaname, relname, indexrelname, idx_scan,
                               idx_tup_read, idx_tup_fetch from pg_stat_all_indexes order by idx_scan desc limit 10;'''
        #冷索引
        cold_index = '''select current_database(),current_database(),relid, indexrelid, schemaname, relname, indexrelname, idx_scan,
                               idx_tup_read, idx_tup_fetch from pg_stat_all_indexes order by idx_scan limit 10;'''
        #全表扫描次数TOP对象
        table_full_count = '''select current_database(),relid,schemaname,relname,seq_scan,seq_tup_read,COALESCE(idx_scan,0) as idx_scan from pg_stat_all_tables order by seq_scan desc limit 10;'''
        #全表扫描返回记录数TOP对象
        table_full_rows = '''select current_database(),relid,schemaname,relname,seq_scan,seq_tup_read,COALESCE(idx_scan,0) as idx_scan from pg_stat_all_tables order by seq_tup_read desc limit 10;'''

        self.db_params = {
            'postgresql'.lower(): [
                {
                    'type': 'dtname',
                    'query': dtname,
                    'desc': "数据库",
                    'fields': ["数据库名"]
                },
            ],
            # 'sqlserver': [{}],
            # 'postgresql': [{}],
            # 'oracle': [{}],
        }

        self.sql_params = {
            'postgresql'.lower(): [
                {
                    'type': 'connnections',
                    'query': connnections,
                    'desc': "连接数",
                    'fields': ["最大连接数", "当前连接数", "剩余连接数"],
                    'zhixing': 'no'
                },
                {
                    'type': 'data_age',
                    'query': data_age,
                    'desc': "数据年龄",
                    'fields': ["datname", "age"],
                    'zhixing': 'no'
                },
                {
                    'type': 'data_size',
                    'query': data_size,
                    'desc': "年龄大于12亿占用的空间数",
                    'fields': ["pg_size_pretty"],
                    'zhixing': 'no'
                },
                {
                    'type': 'surface_expansion',
                    'query': surface_expansion,
                    'desc': "表膨胀",
                    'fields': ["db", "schemaname", "tablename", "tups", "pages", "otta", "tbloat", "wastedpages",
                               "wastedbytes", "wastedsize", "iname", "itups", "ipages", "iotta", "ibloat",
                               "wastedipages", "wastedibytes", "wastedisize", "totalwastedbytes"],
                    'zhixing': 'yes'
                },
                {
                    'type': 'index_inflation',
                    'query': index_inflation,
                    'desc': "索引膨胀",
                    'fields': ["db", "schemaname", "tablename", "tups", "pages", "otta", "tbloat", "wastedpages",
                               "wastedbytes", "wastedsize", "iname", "itups", "ipages", "iotta", "ibloat",
                               "wastedipages", "wastedibytes", "wastedisize", "totalwastedbytes"],
                    'zhixing': 'yes'
                },
                {
                    'type': 'unused_index',
                    'query': unused_index,
                    'desc': "未使用索引",
                    'fields': ["当前数据库", "relid", "indexrelid", "schemaname", "relname", "indexrelname", "idx_scan",
                               "idx_tup_read", "idx_tup_fetch"],
                    'zhixing': 'yes'
                },
                {
                    'type': 'unused_query_table',
                    'query': unused_query_table,
                    'desc': "未使用查询表",
                    'fields': ["当前数据库", "relid", "schemaname", "relname", "seq_scan", "seq_tup_read","idx_scan"],
                    'zhixing': 'yes'
                },
                {
                    'type': 'hot_table',
                    'query': hot_table,
                    'desc': "热表",
                    'fields': ["当前数据库", "relid", "schemaname", "relname", "seq_scan", "seq_tup_read","idx_scan"],
                    'zhixing': 'yes'
                },
                {
                    'type': 'cold_table',
                    'query': cold_table,
                    'desc': "冷表",
                    'fields': ["当前数据库", "relid", "schemaname", "relname", "seq_scan", "seq_tup_read","idx_scan"],
                    'zhixing': 'yes'
                },
                {
                    'type': 'hot_index',
                    'query': hot_index,
                    'desc': "热索引",
                    'fields': ["当前数据库", "relid", "indexrelid", "schemaname", "relname", "indexrelname", "idx_scan",
                               "idx_tup_read", "idx_tup_fetch"],
                    'zhixing': 'yes'
                },
                {
                    'type': 'cold_index',
                    'query': cold_index,
                    'desc': "冷索引",
                    'fields': ["当前数据库", "relid", "indexrelid", "schemaname", "relname", "indexrelname", "idx_scan",
                               "idx_tup_read", "idx_tup_fetch"],
                    'zhixing': 'yes'
                },
                {
                    'type': 'table_full_count',
                    'query': table_full_count,
                    'desc': "全表扫描次数TOP对象",
                    'fields': ["当前数据库", "relid", "schemaname", "relname", "seq_scan", "seq_tup_read","idx_scan"],
                    'zhixing': 'yes'
                },
                {
                    'type': 'table_full_rows',
                    'query': table_full_rows,
                    'desc': "全表扫描返回记录数TOP对象",
                    'fields': ["当前数据库", "relid", "schemaname", "relname", "seq_scan", "seq_tup_read","idx_scan"],
                    'zhixing': 'yes'
                },
            ],
            # 'sqlserver': [{}],
            # 'postgresql': [{}],
            # 'oracle': [{}],
        }

    def get_dbinfo(self, engine):
        """
        根据指定的数据库类型 和 报告内容 进行过滤，返回过滤后的SQL
        """
        return list(self.db_params[engine])


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
    db_list = info_api.get_dbinfo(kwargs['engine'])
    sql_list = info_api.get_info(kwargs['engine'], kwargs["info"])
    # print(json.dumps(sql_list, indent=2, ensure_ascii=False))

    # 2.获取待渲染的报告数据
    db_api = PGHelper(**params)

    for sql in db_list:
        db_results = db_api.col_query(sql["query"])

    sql_api = PGHelper(**params)
    data = []
    for sql in sql_list:
        if sql["zhixing"] == "yes":
            datajsons = []
            for dbname in db_results:
                for db in dbname:
                    params = {
                        'url': kwargs['host'],
                        'port': kwargs['port'],
                        'username': kwargs['user'],
                        'password': kwargs['password'],
                        'dbname': db,
                    }
                    sql_api = PGHelper(**params)
                sql_results = sql_api.col_query(sql["query"])
                for sql_result in sql_results:
                    datajson = dict(zip(sql["fields"], sql_result))
                    datajsons.append(datajson)
            sql["rows"] = json.loads(json.dumps(datajsons, cls=CJsonEncoder, ensure_ascii=False))
            data.append(sql)
            # print(json.dumps(data, cls=CJsonEncoder, ensure_ascii=False, indent=2))
        else:
            sql_results = sql_api.col_query(sql["query"])
            # sql["sql_result"] = sql_results
            datajsons = []
            for sql_result in sql_results:
                datajson = dict(zip(sql["fields"], sql_result))
                datajsons.append(datajson)
            sql["rows"] = json.loads(json.dumps(datajsons, cls=CJsonEncoder, ensure_ascii=False))
            data.append(sql)
        # print(json.dumps(data, cls=CJsonEncoder, ensure_ascii=False, indent=2))




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
        info = ['connnections','data_age','data_size','surface_expansion','index_inflation','unused_index','unused_query_table','hot_table','cold_table','hot_index','cold_index','table_full_count','table_full_rows']
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
