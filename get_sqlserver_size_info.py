import json
import datetime
import decimal
import os
import json
import time
import locale
# 3rd-part Modules
import argparse
from jinja2 import Template
import pymssql

locale.setlocale(locale.LC_CTYPE,'chinese')
os.environ['NLS_LANG'] = 'SIMPLIFIED CHINESE_CHINA.UTF8'


class CJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(obj, decimal.Decimal):
            return str(obj)
        else:
            return json.JSONEncoder.default(self, obj)


class MssqlHelper:
    """MSSQL驱动连接驱动"""

    def __init__(self, **kwargs):

        try:
            self.conn = pymssql.connect(**{
                'host': kwargs.get('host'),
                'port': int(kwargs.get('port')),
                'user': kwargs.get('user'),
                'password': kwargs.get('password'),
                'database': kwargs.get('dbname'),
                'charset': 'utf8',
                'autocommit': True
            })
        except Exception as e:
            print(e)
            print('账号无效, 请检查权限或密码!')

    def col_query(self, sql):
        """数据查询操作"""
        # 使用cursor()方法获取操作游标
        cursor = self.conn.cursor()
        # SQL 查询语句
        try:
            # 执行SQL语句
            cursor.execute(sql)
            result = cursor.fetchall()
            self.conn.commit()
            return result
        except Exception as e:
            print("Error: unable to fecth data %s " % e)
            return '执行失败, %s' % str(e), False

        finally:
            # print('query cursor closed')
            cursor.close()

    def update(self, sql):
        """数据更新操作"""

        # 使用cursor()方法获取操作游标
        cursor = self.conn.cursor()

        # SQL 查询语句
        try:
            # 执行SQL语句
            list(cursor.execute(sql))
            # 获取所有记录列表
            self.conn.commit()
            return 0, '执行成功', True
        except Exception as e:
            print("Error: unable to fecth data %s " % e)
            return 1, '执行失败, %s' % str(e), False

        finally:
            print('update cursor closed')
            cursor.close()


class MssqlInfo:
    """
    获取报告需要的后端逻辑
    """

    def __init__(self):
        """
        数据库后端逻辑
        """
        mssql_db_size = """with fs
            as
            (
                select database_id, type, size * 8.0  size
                from sys.master_files
            )
            select 
                name,
                (select   cast(round(sum(size),2)   as   numeric(15,2))  from fs where type = 0 and fs.database_id = db.database_id) DataFileSizeMB,
                (select cast(round(sum(size),2)   as   numeric(15,2))  from fs where type = 1 and fs.database_id = db.database_id) LogFileSizeMB
            from sys.databases db
            order by 2 desc;"""
        mssql_table_size = """select top 20 N'tablename' = name ,
            cast(rows as varchar) + '行'rows,
            reservedpages * 8 db_size,
            pages * 8 data_size,
            (usedpages - pages) * 8 index_size,
            (reservedpages - usedpages) * 8 unused_size
            FROM
            (select name,id,
            reservedpages = sum(a.total_pages),
            usedpages = sum(a.used_pages),
            pages = sum(
            CASE
            When a.type <> 1 Then a.used_pages
            When p.index_id < 2 Then a.data_pages
            Else 0
            END
            ),
            rows = sum(
            CASE
            When (p.index_id < 2) and (a.type = 1) Then p.rows
            Else 0
            END
            )
            from sys.partitions p, sys.allocation_units a,sysobjects o
            where p.partition_id = a.container_id and p.object_id = o.id
            group by name,id
            ) a
            order by reservedpages desc"""

        self.sql_params = {
            'SQLServer'.lower(): [
                {
                    'type': 'db_size',
                    'query': mssql_db_size,
                    'desc': "库空间统计",
                    'fields': ["数据库名", "数据大小", "索引大小"]
                },
                {
                    'type': 'table_size',
                    'query': mssql_table_size,
                    'desc': "表空间统计",
                    'fields': ["表名", "行数", "已分配空间", "数据空间", "索引空间", "未使用空间"]
                }
            ],
            # 'mysql': [{}],
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
        html_string_head= """<!doctype html>
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
        <h3 class="title text-center">阿里云RDS For SQLServer 库表统计报告</h3>
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
        'host': kwargs['host'],
        'port': kwargs['port'],
        'user': kwargs['user'],
        'password': kwargs['password'],
        'dbname': kwargs['dbname'],
    }
    # 1.根据传递的参数对报告后端逻辑进行过滤
    info_api = MssqlInfo()
    sql_list = info_api.get_info(kwargs['engine'], kwargs["info"])
    # print(json.dumps(sql_list, indent=2, ensure_ascii=False))

    # 2.获取待渲染的报告数据
    mssql_api = MssqlHelper(**params)
    data = []
    for sql in sql_list:
        sql_result = mssql_api.col_query(sql["query"])
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
    parser = argparse.ArgumentParser(description='''SQLServer 库表统计报告小工具
关于数据库的整体库表空间使用情况	
1. 库空间统计
2. 表空间统计
Example：
    python3 get_sqlserver_size_info.py --Engine ENGINE --Host HOST --Port PORT --User USER --Password PASSWORD --DBName DBNAME --Info INFO
    python3 get_sqlserver_size_info.py --Engine SQLServer --Host 10.200.6.55 --Port 1433 --User sa --Password "Zyadmin@123" --DBName ecology --Info db_size,table_size --OutDir report
    python3 get_sqlserver_size_info.py --Engine SQLServer --Host 10.200.6.55 --Port 1433 --User sa --Password "Zyadmin@123" --DBName ecology --Info db_size,table_size --OutDir report > tmp.txt 

''', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--Engine", help='''Engine 必要参数
    只能选择一种类型 支持的所有类型：SQLServer''')
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

    if args.Engine.lower() == 'SQLServer'.lower():
        starup(**params)
    else:
        print('请选择SQLServer类型的数据库。')
