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
            # self.cur = self.conn.cursor(cursor=pymysql.cursors.DictCursor)
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


class GetReport:
    """
    渲染数据库报告到前端
    """

    def __init__(self, **kwargs):
        self.render_data = kwargs

    def render_template(self):
        template_data = """

        {% for _data in data %}
            <div class="new_container">
                            <dl class="row">
                                <dt class="col-sm-3">{{ _data.desc }}</dt>
                            </dl>
                    <table class="table table-striped">
                        <thead>
                        <tr>
                            <th scope="col">序号</th>
                            {% for field in _data.fields %}
                            <th scope="col">{{ field }}</th>
                            {% endfor %}
                        </tr>
                        </thead>
                                            {% for _row in _data.sql_result %}        
                                                    <tr>
                                                        <th scope="row">{{ loop.index }}</th>
                                                        {% for col in _row %}
                                                        {% if col | float %}
                                                        <td>{{ col | filesizeformat}}</td>
                                                        {% else %}
                                                        <td>{{ col }}</td>
                                                        {% endif %}
                                                        {% endfor %}
                                                    </tr>
                                            {% endfor %}        

                    </table>
                </div>
        {% endfor %}


</div>
<!-- Optional JavaScript -->
<!-- jQuery first, then Popper.js, then Bootstrap JS -->
<script src="https://cdn.jsdelivr.net/npm/jquery@3.4.1/dist/jquery.slim.min.js"
        integrity="sha384-J6qa4849blE2+poT4WnyKhv5vZF5SrPo0iEjwBvKU7imGFAV0wwj1yYfoRSJoZ+n"
        crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/npm/popper.js@1.16.0/dist/umd/popper.min.js"
        integrity="sha384-Q6E9RHvbIyZFJoft+2mJbHaEWldlvI9IOYy5n3zV9zzTtmI3UksdQRVvoxMfooAo"
        crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@4.4.1/dist/js/bootstrap.min.js"
        integrity="sha384-wfSDF2E50Y2D1uUdj0O3uMBJnjuUD4Ih7YwaYd1iqfktj0Uod8GCExl3Og8ifwB6"
        crossorigin="anonymous"></script>
</body>
</html>
"""

        template = Template(template_data)
        return template.render(**self.render_data)

    def maker(self, out_dir):
        # 因为CSS中存在{{因此不能放在template_data中渲染
        html_string_head = """<!doctype html>
<html lang="en">
<head>
    <!-- Required meta tags -->
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">

    <!-- Bootstrap CSS -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.4.1/dist/css/bootstrap.min.css"
          integrity="sha384-Vkoo8x4CGsO3+Hhxv8T/Q5PaXtkKtu6ug5TOeNV6gBiFeWPGFN9MuhOf23Q9Ifjh" crossorigin="anonymous">

    <title>>阿里云RDS For SQLServer 库表统计报告</title>
    <style type="text/css">
      .new_container {
            margin-top: 10px;
        }

      .summary {
            margin-top: 30px;
        }

       .col-sm-3 {
            margin-top: 10px;
        }


    </style>
</head>
"""

        html_string_1 = """
<body>
<div class="container">
    <div class="card-body">
        <h3 class="title text-center">阿里云RDS For MySQL 库表统计报告</h3>
        <div class="row text-muted">
            <div class="col-md-12 text-center">报告时间： {0} </div>
        </div>
        <p class=summary>
            尊敬的客户您好，本文档为实时数据库报告，通过本报告能够反映当前数据库的情况。本文档的一切解释权归驻云科技有限公司所有，如有问题，请联系您的客户技术经理或服务工程师咨询</p>
    </div>
        """.format(time.strftime('%Y年%m月%d日 %H:%M:%S', time.localtime(time.time())))
        html_string_2 = self.render_template()
        # print('\n'.join([html_string_0, html_string_1]))
        file_name = 'report-{time_string}.html'.format(
            time_string=time.strftime('%Y%m%d%H%M%S', time.localtime(time.time())))
        with open('{}/{}'.format(out_dir, file_name), 'w', encoding='utf8') as f:
            f.write('\n'.join([html_string_head, html_string_1, html_string_2]))


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
        sql_result = sql_api.col_query(sql["query"])
        sql["sql_result"] = sql_result
        data.append(sql)
    print(json.dumps(data, cls=CJsonEncoder, ensure_ascii=False, indent=2))

    # 3.渲染报告
    temp_data = {
        'data': data,
    }
    report = GetReport(**temp_data)
    report.maker(kwargs['out_dir'])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='''MySQL 库表统计报告小工具
关于数据库的整体库表空间使用情况	
1. 库空间统计
2. 表空间统计
Example：
    python3 get_mysql_size_info.py --Engine ENGINE --Host HOST --Port PORT --User USER --Password PASSWORD --DBName DBNAME --Info INFO
    python3 get_mysql_size_info.py --Engine mysql --Host 10.0.0.29 --Port 3306 --User supercloud_dev --Password "Zyadmin@123" --DBName supercloud_dev --Info db_size,table_size --OutDir report
    python3 get_mysql_size_info.py --Engine mysql --Host 10.0.0.29 --Port 3306 --User supercloud_dev --Password "Zyadmin@123" --DBName supercloud_dev --Info db_size,table_size --OutDir report > tmp.txt 

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
        info = ['db_size', 'table_size']
    elif len(args.Info.split(',')):
        info = args.Info.split(',')
    params = {
        'info': args.Info,
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

