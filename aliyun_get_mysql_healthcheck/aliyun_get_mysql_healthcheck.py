# -*- coding: utf-8 -*-
"""
输出目标 MySQL 数据库库表信息
"""
# Build-in Modules
import json
import datetime
import decimal
import time

# 3rd-part Modules
import pymysql
import argparse
from jinja2 import Template
from aliyun_get_mysql_healthcheck_outhtml import GetReport
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


class MysqlHelper:
    def __init__(self, **kwargs):
        self.url = kwargs['url']
        self.port = int(kwargs['port'])
        self.username = kwargs['username']
        self.password = kwargs['password']
        self.dbname = kwargs['dbname']
        self.charset = "utf8"
        try:
            self.conn = pymysql.connect(host=self.url, user=self.username, passwd=self.password, port=self.port,
                                        charset=self.charset, db=self.dbname)
            #self.cur = self.conn.cursor(cursor=pymysql.cursors.DictCursor)
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
        mysql_db_size = '''SELECT 
                table_schema,
                ROUND(SUM(data_length), 2) AS data_length_B,
                ROUND(SUM(index_length), 2) AS index_length_B,
                ROUND(SUM((data_length + index_length)), 2) AS total_length_B
                FROM information_schema.tables
                GROUP BY table_schema
                ORDER BY data_length_B DESC , index_length_B DESC'''
        mysql_table_size = '''SELECT 
                t.table_name 表,
                t.table_schema 库,
                t.engine 引擎,
                t.table_length_B 表空间,
                t.table_length_B/t1.all_length_B 表空间占比,
                t.data_length_B 数据空间,
                t.index_length_B 索引空间,
                t.table_rows 行数,
                t.avg_row_length_B 平均行长
            FROM
                (
                SELECT 
                    table_name,
                        table_schema,
                        ENGINE,
                        table_rows,
                        data_length +  index_length AS table_length_B,
                        data_length AS data_length_B,
                        index_length AS index_length_B,
                        AVG_ROW_LENGTH AS avg_row_length_B
                FROM
                    information_schema.tables
                WHERE
                    table_schema NOT IN ('mysql' , 'performance_schema', 'information_schema', 'sys') and table_type != 'VIEW'
                    ) t
                    join (
                    select sum((data_length + index_length)) as all_length_B from information_schema.tables
                    ) t1;'''
        mysql_auto_id = '''select  table_schema    as "库",
        table_name      as "表",
        engine          as "存储引擎",
        auto_increment  as "自增id"
from information_schema.tables
where table_schema not in ("mysql", "information_schema", "performance_schema", "sys")
order by table_schema asc;'''
        mysql_no_innodb = '''select  table_schema    as "库",
        table_name      as "表",
        engine          as "存储引擎"
from information_schema.tables
where engine != "InnoDB";'''
        mysql_part_index = '''
SELECT TABLE_SCHEMA as "库", TABLE_NAME "表", INDEX_NAME as "索引名", SEQ_IN_INDEX as "索引序列", COLUMN_NAME as "列", CARDINALITY as "基数", SUB_PART "前缀长度"
FROM INFORMATION_SCHEMA.STATISTICS
WHERE SUB_PART > 10 ORDER BY SUB_PART DESC;
'''
        mysql_long_index='''select IFNULL(c.table_schema,'')  as "库",
       IFNULL(c.table_name,'') as "表", 
       IFNULL(c.COLUMN_NAME,'') as "列",
       IFNULL(c.DATA_TYPE,"")  as "数据类型",
       IFNULL(c.CHARACTER_MAXIMUM_LENGTH,'') as "列的长度",
       IFNULL(c.CHARACTER_OCTET_LENGTH,'') as "列的大小",
       IFNULL(s.NON_UNIQUE,'') as "是否唯一",
       IFNULL(s.INDEX_NAME,'') as "索引名称",
       IFNULL(s.CARDINALITY,'') as "基数",
       IFNULL(s.SUB_PART,'') as "前缀长度",
       IFNULL(s.NULLABLE,'') as "是否为空"
from information_schema.COLUMNS c inner join information_schema.STATISTICS s
 using(table_schema, table_name, COLUMN_NAME)
where
 c.table_schema not in ("mysql", "sys", "performance_schema", "information_schema", "test") and
 c.DATA_TYPE in ("varchar", "char", "text", "blob") and
 ((CHARACTER_OCTET_LENGTH > 20 and SUB_PART is null) or
 SUB_PART * CHARACTER_OCTET_LENGTH/CHARACTER_MAXIMUM_LENGTH >20);
'''
        no_submission_transaction='''select IFNULL(b.host,'') as "来源主机", 
IFNULL(b.user,'') as "用户", 
IFNULL(b.db,'') as"库", 
IFNULL(b.time,'') as "时间", 
IFNULL(b.COMMAND,'') as "执行语句", 
IFNULL(a.trx_id,'') as "事务号", 
IFNULL(a. trx_state,'') as "事务状态"
from information_schema.innodb_trx a left join 
information_schema.PROCESSLIST b on a.trx_mysql_thread_id = b.id;
'''
        # 查看当前有无行锁等待事件
        mysql56_row_lock_wait = '''
        SELECT lw.requesting_trx_id AS request_XID,
         trx.trx_mysql_thread_id as request_mysql_PID,
         trx.trx_query AS request_query,
         lw.blocking_trx_id AS blocking_XID,
         trx1.trx_mysql_thread_id as blocking_mysql_PID,
         trx1.trx_query AS blocking_query, lo.lock_index AS lock_index
        FROM
         information_schema.innodb_lock_waits lw INNER JOIN
         information_schema.innodb_locks lo
         ON lw.requesting_trx_id = lo.lock_trx_id INNER JOIN
         information_schema.innodb_locks lo1
         ON lw.blocking_trx_id = lo1.lock_trx_id INNER JOIN
         information_schema.innodb_trx trx
         ON lo.lock_trx_id = trx.trx_id INNER JOIN
         information_schema.innodb_trx trx1
         ON lo1.lock_trx_id = trx1.trx_id;
        '''
        # 其实，在MySQL 5.7下，也可以直接查看sys.innodb_lock_waits视图
        mysql57_row_lock_wait = '''select
wait_started                ,
wait_age                    ,
wait_age_secs               ,
locked_table                ,
locked_table_schema         ,
locked_table_name           ,
locked_table_partition      ,
locked_table_subpartition   ,
locked_index                ,
locked_type                 ,
waiting_trx_id              ,
waiting_trx_started         ,
waiting_trx_age             ,
waiting_trx_rows_locked     ,
waiting_trx_rows_modified   ,
waiting_pid                 ,
waiting_query               ,
waiting_lock_id             ,
waiting_lock_mode           ,
blocking_trx_id             ,
blocking_pid                ,
blocking_query              ,
blocking_lock_id            ,
blocking_lock_mode          ,
blocking_trx_started        ,
blocking_trx_age            ,
blocking_trx_rows_locked    ,
blocking_trx_rows_modified  ,
sql_kill_blocking_query     ,
sql_kill_blocking_connection
from sys.innodb_lock_waits;'''

        # 检查哪些表没有显式创建主键索引
        no_primary_index_table = '''
        SELECT
        a.TABLE_SCHEMA as "库",
        a.TABLE_NAME as "表"
        FROM
        (
        SELECT
        TABLE_SCHEMA,
        TABLE_NAME
        FROM
        information_schema.TABLES
        WHERE
        TABLE_SCHEMA NOT IN (
        "mysql",
        "sys",
        "information_schema",
        "performance_schema"
        ) AND
        TABLE_TYPE = "BASE TABLE"
        ) AS a
        LEFT JOIN (
        SELECT
        TABLE_SCHEMA,
        TABLE_NAME
        FROM
        information_schema.TABLE_CONSTRAINTS
        WHERE
        CONSTRAINT_TYPE = "PRIMARY KEY"
        ) AS b ON a.TABLE_SCHEMA = b.TABLE_SCHEMA
        AND a.TABLE_NAME = b.TABLE_NAME
        WHERE
        b.TABLE_NAME IS NULL;
        '''

        # 查看InnoDB表碎片率
        table_fragment = '''SELECT TABLE_SCHEMA as '库', 
TABLE_NAME as '表',
IFNULL(1-(TABLE_ROWS*AVG_ROW_LENGTH)/(DATA_LENGTH + INDEX_LENGTH + DATA_FREE),'') AS '碎片率'
FROM information_schema.TABLES WHERE
TABLE_SCHEMA NOT IN ("mysql", "information_schema", "performance_schema", "sys")
ORDER BY 碎片率 DESC;
        '''


        self.sql_params = {
            'mysql'.lower(): [
                {
                    'type': 'db_size',
                    'query': mysql_db_size,
                    'desc': "库空间统计",
                    'fields': ["数据库名", "数据大小", "索引大小", "总大小"]
                },
                {
                    'type': 'table_size',
                    'query': mysql_table_size,
                    'desc': "表空间统计",
                    'fields': ["表", "库", "引擎", "表空间", "表空间占比", "数据空间", "索引空间", "行数", "平均行长"]
                },
                {
                    'type': 'auto_id',
                    'query': mysql_auto_id,
                    'desc': "自增ID统计",
                    'fields': ["库", "表", "存储引擎", "自增id"]
                },
                {
                    'type': 'no_innodb',
                    'query': mysql_no_innodb,
                    'desc': "非innodb存储引擎的表",
                    'fields': ["库", "表", "存储引擎"]
                },
                {
                    'type': 'part_index',
                    'query': mysql_part_index,
                    'desc': "前缀索引",
                    'fields': ["库", "表", "索引名", "索引序列", "列", "基数", "前缀长度"]
                },
                {
                    'type': 'long_index',
                    'query': mysql_long_index,
                    'desc': "索引长度超过30字节",
                    'fields': ["库", "表", "列", "数据类型", "列的长度", "列的大小", "是否唯一", "索引名称", "基数", "前缀长度", "是否为空"]
                },
                {
                    'type': 'no_submission_transaction',
                    'query': no_submission_transaction,
                    'desc': "未完成的事务列表",
                    'fields': ["来源主机", "用户", "库", "时间", "执行语句", "事务号", "事务状态"]
                },
                {
                    'type': 'row_lock_wait',
                    'query': mysql57_row_lock_wait,
                    'desc': "行锁等待事件",
                    'fields': ["wait_started", "wait_age", "wait_age_secs", "locked_table", "locked_table_schema", "locked_table_name", "locked_table_partition", "locked_table_subpartition", "locked_index", "locked_type", "waiting_trx_id", "waiting_trx_started", "waiting_trx_age", "waiting_trx_rows_locked", "waiting_trx_rows_modified", "waiting_pid", "waiting_query", "waiting_lock_id", "waiting_lock_mode", "blocking_trx_id", "blocking_pid", "blocking_query", "blocking_lock_id", "blocking_lock_mode", "blocking_trx_started", "blocking_trx_age", "blocking_trx_rows_locked", "blocking_trx_rows_modified", "sql_kill_blocking_query", "sql_kill_blocking_connection"]
                },
                {
                    'type': 'no_primary_index_table',
                    'query': no_primary_index_table,
                    'desc': "没有显式主键索引表",
                    'fields': ["库", "表"]
                },
                {
                    'type': 'table_fragment',
                    'query': table_fragment,
                    'desc': "表碎片",
                    'fields': ["库", "表", "碎片率"]
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
    sql_api = MysqlHelper(**params)
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
    parser = argparse.ArgumentParser(description='''MySQL 库表统计报告小工具
关于数据库的整体库表空间使用情况	
1. 库空间统计
2. 表空间统计
Example：
    python3 aliyun_get_mysql_healthcheck.py --Engine ENGINE --Host HOST --Port PORT --User USER --Password PASSWORD --DBName DBNAME --Info INFO
    python3 aliyun_get_mysql_healthcheck.py --Engine mysql --Host 10.0.0.29 --Port 3306 --User supercloud_dev --Password "Zyadmin@123" --DBName supercloud_dev --Info db_size,table_size --OutDir report
    python3 aliyun_get_mysql_healthcheck.py --Engine mysql --Host 10.0.0.29 --Port 3306 --User supercloud_dev --Password "Zyadmin@123" --DBName supercloud_dev --Info db_size,table_size --OutDir report > tmp.txt 

''', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--Engine", help='''Engine 必要参数
    只能选择一种类型 支持的所有类型：MySQL 不区分大小写''')
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
        info = ['db_size', 'table_size', 'audo_id', 'no_innodb', 'part_index', 'long_index', 'no_submission_transaction', 'row_lock_wait', 'no_primary_index_table', 'table_fragment']
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

    if args.Engine.lower() == 'MySQL'.lower():
        starup(**params)
    else:
        print('请选择 MySQL 类型的数据库。')