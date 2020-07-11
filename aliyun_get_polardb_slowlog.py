# -*- coding: utf-8 -*-
"""
==========================================================================================
请求参数案例1（默认AK传空值为STS Token验证方式，RoleName为空的默认值为ZhuyunFullReadOnlyAccess）:
        'AccessKeyId': None,
        'AccessKeySecret': None,
        'RoleName': None,
请求参数案例2（AK值不为空的时候，为普通的AK验证方式，这时候如果RoleName为非空，STS Token验证方式也不生效）:
        'AccessKeyId': XXXXXXXXXXXXXX,
        'AccessKeySecret': XXXXXXXXXXXXXX,
        'RoleName': None,
请求参数案例3（默认AK传空值为STS Token验证方式，RoleName不为空，RoleName为设置的值）:
        'AccessKeyId': None,
        'AccessKeySecret': None,
        'RoleName': XXXXXXXXXXXXXX,
==========================================================================================
"""
# Build-in Modules
import json
import time
import datetime

# 3rd-part Modules
import argparse
from aliyun_sdk import client
from jinja2 import Template


class Custom:
    def __init__(self):
        pass

    def get_config(self, **kwargs):
        self.out = kwargs
        self.aliyun = client.AliyunClient(config=kwargs)

    def get_describe_regions(self):
        try:
            status_code, api_res = self.aliyun.common("polardb", Action="DescribeRegions")
            region_ids = list(set(map(lambda x: x['RegionId'], api_res['Regions']['Region']
                                      )))
        except Exception as e:
            print(str(e))
            region_ids = []
        # print(region_ids)
        return region_ids

    def get_describe_db_clusters(self, common_region_ids, db_engines):
        """
        1. 循环所有地域获取所有RDS实例；
        2. 再过滤出指定的数据库类型。
        """
        instance_list = []

        for region_id in common_region_ids:
            page_num = 1
            while True:
                # 循环获取实例
                try:
                    status_code, api_res = self.aliyun.common("polardb", Action="DescribeDBClusters",
                                                              RegionId=region_id,
                                                              PageSize=100,
                                                              PageNumber=page_num)
                except Exception as e:
                    print(str(e))

                if not api_res.get("Items", {}).get("DBCluster", []):
                    break

                # 过滤出指定数据库Engines
                instance_list = instance_list + list(map(
                    lambda x: {"DBClusterId": x.get("DBClusterId"),
                               "RegionId": x["RegionId"]},
                    list(filter(lambda x: x["DBType"] in db_engines,
                                api_res.get("Items", {}).get("DBCluster", [])))))

                page_num = page_num + 1
        return instance_list

    def get_describe_db_cluster_attribute(self, **kwargs):
        """
        :param kwargs:  {
                            "DBClusterId": "DBClusterId"
                        }
        :return: {}
        """
        try:
            status_code, api_res = self.aliyun.common("polardb", Action="DescribeDBClusterAttribute", **kwargs)
            # print(json.dumps(api_res, indent=2))
        except Exception as e:
            print(str(e))
            print("获取PolarDB集群明细信息")
            api_res = {}

        # print(json.dumps(api_res, indent=2))
        return api_res

    def get_describe_slow_logs(self, **kwargs):
        """
        调用该接口时，集群必须为MySQL 5.6或8.0版本。
        获取PolarDB集群慢查询
        kwargs = {
        "DBClusterId": "",
        "RegionId,"",
        "EndTime":"",
        "StartTime":"",
        "SortKey":""
        }

        """
        try:
            status_code, api_res = self.aliyun.common("polardb", Action="DescribeSlowLogs", **kwargs)
            # print(api_res)
        except Exception as e:
            print(str(e))
            print("获取PolarDB集群慢查询")
            api_res = {}
        return api_res

    def get_describe_slow_log_records(self, **kwargs):
        """
        https://help.aliyun.com/document_detail/147045.html?spm=a2c4g.11174283.6.1558.c69625deTFnKMc
        该接口用于查看POLARDB集群的慢日志明细。调用该接口时，集群必须为MySQL 5.6或8.0版本。
        :param kwargs:
        kwargs = {
        "DBClusterId": "",
        "RegionId,"",
        "EndTime":"",
        "StartTime":"",
        "DBName":"",
        "SQLHASH":"",
        }
        :return:
        """
        try:
            status_code, api_res = self.aliyun.common("polardb", Action="DescribeSlowLogRecords", **kwargs)
        except Exception as e:
            print(str(e))
            print("获取PolarDB慢查询")
            api_res = {}
        return api_res

    def get_top_10(self, slow_query):
        """
        获取按照执行次数最多，执行时间最长排序的前10条SQL
        order_by_TotalExecutionCounts_MaxExecutionTime
        :return: list
        """
        if isinstance(slow_query, list) and slow_query:
            items = slow_query[:10]
            """
            list中根据字典的某个key或多个key进行排序，倒
            """
            items.sort(key=lambda x: (x['TotalExecutionCounts'], x['MaxExecutionTime']), reverse=True)
            return items
        else:
            return []

    def start_up(self, **kwargs):
        # 1.获取实例
        # 1.1 按照地域和数据库引擎过滤实例ID
        instance_list = self.get_describe_db_clusters(kwargs['common_region_ids'], kwargs['db_engines'])
        # 过滤实例ID
        if kwargs['filter_instance']:
            filter_instance_list = list(
                filter(lambda x: x['DBClusterId'] in kwargs['DBClusterIds'], instance_list))
        else:
            filter_instance_list = instance_list
        # print(filter_instance_list)

        # 2 获取慢查询信息
        # 2.1 获取已过滤的实例的慢查询
        params = list(map(
            lambda x:
            {
                "DBClusterId": x["DBClusterId"],
                "RegionId": x["RegionId"],
                "StartTime": (datetime.datetime.now() - datetime.timedelta(hours=24)).strftime("%Y-%m-%dZ"),
                "EndTime": (datetime.datetime.now() - datetime.timedelta(hours=0)).strftime("%Y-%m-%dZ"),
                "SortKey": "TotalExecutionCounts"
            }, filter_instance_list

        ))
        # print(params)
        result = []
        for ins_params in params:
            try:
                response = self.get_describe_slow_logs(**ins_params)["Items"]["SQLSlowLog"]
                sql_list = self.get_top_10(response)

                # print(sql_list)
                # 目前PolarDB与RDS接口返回值不一致，返回key中不包含SQLHASH
                # 通过 SQLHASH 获取SQL的执行账号和客户端
                # 'SQLHASH': '18122c83b8203a7028a0e3c92b88bc3a'
                for _sql in sql_list:
                    sql_hash = {
                        "DBClusterId": ins_params['DBClusterId'],
                        "RegionId": ins_params["RegionId"],
                        "StartTime": (datetime.datetime.now() - datetime.timedelta(hours=48)).strftime(
                            "%Y-%m-%dT00:00Z"),
                        "EndTime": (datetime.datetime.now() - datetime.timedelta(hours=0)).strftime("%Y-%m-%dT08:00Z"),
                        "SQLHASH": _sql["SQLHASH"],
                    }
                    # print(json.dumps(sql_hash))
                    hash_response = self.get_describe_slow_log_records(**sql_hash)
                    if hash_response.get('Items', {}).get('SQLSlowRecord', []):
                        _sql['HostAddress'] = hash_response['Items']['SQLSlowRecord'][0]["HostAddress"]
                    else:
                        _sql['HostAddress'] = ''
                        print(json.dumps(hash_response))

                slow_log = {
                    "DBClusterId": ins_params['DBClusterId'],
                    "sql_list": sql_list
                }
            except Exception as e:
                print(str(e))
                slow_log = {}
            result.append(slow_log)
        # print(result)

        # 循环所有的实例，打印报告
        for instance_slow_logs in result:
            report = GetReport(**instance_slow_logs)
            report.maker(kwargs["out_dir"])


class GetReport:
    def __init__(self, **kwargs):
        self.render_data = kwargs

    def render_template(self):
        template_data = """    <div class="app-page-title">
        <div class="row col-12">
            <div class="col-md-12">
                <div class="main-card mb-3 card">
                    <div class="card-header"> PolarDB 集群ID：{{ DBClusterId }} 每日慢SQL TOP 10 明细
                    </div>
                    <div class="table-responsive">
                        <table class="align-middle mb-0 table table-borderless table-striped table-hover">
                            <thead>
                            <tr>
                                <th class="text-center table-title-heading">序号</th>
                                <th class="text-center table-title-heading">集群ID</th>
                                <th class="text-center table-title-heading">节点ID</th>
                                <th class="text-center table-title-heading">执行用户和地址</th>
                                <th class="text-center table-title-heading">执行次数</th>
                                <th class="text-center table-title-heading">执行时间</th>
                                <th class="text-center table-title-heading">慢查询</th>
                            </tr>
                            </thead>
                                    {% for sql in sql_list %}
                                        <tr>
                                            <td class="text-center table-title-subheading">{{ loop.index }}</td>
                                            <td class="text-center table-title-subheading">{{ DBClusterId }}</td>
                                            <td class="text-center table-title-subheading">{{ sql.DBNodeId }}</td>
                                            <td class="text-center table-title-subheading">{{ sql.HostAddress }}</td>
                                            <td class="text-center table-title-subheading">{{ sql.TotalExecutionCounts }}</td>
                                            <td class="text-center table-title-subheading">{{ sql.MaxExecutionTime }}</td>
                                            <td class="text-center table-title-subheading">
                                                <div class="accordion" id="accordionExample">
                                                    <h2 class="mb-0">
                                                        <button class="btn btn-link btn-block text-left collapsed table-title-subheading"
                                                                type="button" data-toggle="collapse"
                                                                data-target="#collapseThree" aria-expanded="false"
                                                                aria-controls="collapseThree">
                                                            {{ sql.SQLText |truncate(30) }}
                                                        </button>
                                                    </h2>

                                                    <div id="collapseThree" class="collapse" aria-labelledby="headingThree"
                                                         data-parent="#accordionExample">
                                                            {{ sql.SQLText }}
                                                    </div>
                                                </div>
                                            </td>
                                        </tr>
                                    {% endfor %}

                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/jquery@3.4.1/dist/jquery.slim.min.js"
            integrity="sha384-J6qa4849blE2+poT4WnyKhv5vZF5SrPo0iEjwBvKU7imGFAV0wwj1yYfoRSJoZ+n"
            crossorigin="anonymous"></script>
        <script src="https://cdn.jsdelivr.net/npm/popper.js@1.16.0/dist/umd/popper.min.js"
            integrity="sha384-Q6E9RHvbIyZFJoft+2mJbHaEWldlvI9IOYy5n3zV9zzTtmI3UksdQRVvoxMfooAo"
            crossorigin="anonymous"></script>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@4.4.1/dist/js/bootstrap.min.js"
            integrity="sha384-wfSDF2E50Y2D1uUdj0O3uMBJnjuUD4Ih7YwaYd1iqfktj0Uod8GCExl3Og8ifwB6"
            crossorigin="anonymous"></script>
    </div>
</div>
</body>
</html>
"""

        template = Template(template_data)
        return template.render(**self.render_data)

    def maker(self, out_dir):
        # 因为CSS中存在{{因此不能放在template_data中渲染
        html_string_0 = """<!doctype html>
<html lang="en">
<head>
    <!-- Required meta tags -->
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <!-- Bootstrap CSS -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.4.1/dist/css/bootstrap.min.css"
          integrity="sha384-Vkoo8x4CGsO3+Hhxv8T/Q5PaXtkKtu6ug5TOeNV6gBiFeWPGFN9MuhOf23Q9Ifjh" crossorigin="anonymous">

    <style type="text/css">
        .app-page-title {
            padding-top: 60px;
            flex: 1;
            display: flex;
            z-index: 8;
            position: relative
        }

        .page-title-icon {
            font-size: 2rem;
            display: flex;
            align-items: center;
            align-content: center;
            text-align: center;
            padding: .83333rem;
            margin: 0 30px 0 0;
            background: #fff;
            box-shadow: 0 0.46875rem 2.1875rem rgba(4, 9, 20, 0.03), 0 0.9375rem 1.40625rem rgba(4, 9, 20, 0.03), 0 0.25rem 0.53125rem rgba(4, 9, 20, 0.05), 0 0.125rem 0.1875rem rgba(4, 9, 20, 0.03);
            border-radius: .25rem;
            width: 60px;
            height: 60px
        }

        .page-title-subheading {
            padding: 3px 0 0;
            font-size: .88rem;
            opacity: .6
        }

        .page-title-heading {
            font-size: 1.25rem;
            font-weight: 400;

        }

        .table-title-heading {
            font-size: .5rem;
            opacity: .9
        }

        .table-title-subheading {
            font-size: .5rem;
            opacity: .6
        }

        .card-header {
            padding: 10px 10px 10px;
            font-size: .5rem;
            opacity: .6;
            font-family: verdana;
        }

    </style>
</head>


<body>
<div class="container-fluid">
    <div class="app-page-title">
        <div class="row">
            <div class="col col-2">
                <div class="page-title-icon">
                    <svg t="1584605510076" class="icon" viewBox="0 0 1024 1024" version="1.1"
                         xmlns="http://www.w3.org/2000/svg" p-id="1171" width="200" height="200">
                        <path d="M312.1 591.5c3.1 3.1 8.2 3.1 11.3 0l101.8-101.8 86.1 86.2c3.1 3.1 8.2 3.1 11.3 0l226.3-226.5c3.1-3.1 3.1-8.2 0-11.3l-36.8-36.8c-3.1-3.1-8.2-3.1-11.3 0L517 485.3l-86.1-86.2c-3.1-3.1-8.2-3.1-11.3 0L275.3 543.4c-3.1 3.1-3.1 8.2 0 11.3l36.8 36.8z"
                              p-id="1172"></path>
                        <path d="M904 160H548V96c0-4.4-3.6-8-8-8h-56c-4.4 0-8 3.6-8 8v64H120c-17.7 0-32 14.3-32 32v520c0 17.7 14.3 32 32 32h356.4v32L311.6 884.1c-3.7 2.4-4.7 7.3-2.3 11l30.3 47.2v0.1c2.4 3.7 7.4 4.7 11.1 2.3L512 838.9l161.3 105.8c3.7 2.4 8.7 1.4 11.1-2.3v-0.1l30.3-47.2c2.4-3.7 1.3-8.6-2.3-11L548 776.3V744h356c17.7 0 32-14.3 32-32V192c0-17.7-14.3-32-32-32z m-40 512H160V232h704v440z"
                              p-id="1173"></path>
                    </svg>

                </div>
            </div>
            <div class="col">
                <div class="page-title-heading">
                    阿里云 PolarDB集群 慢日志日报
                    <div class="page-title-subheading">AliYun PolarDB Cluster Slow Log Daily Report
                    </div>
                </div>
            </div>
        </div>
    </div>
        """
        html_string_1 = self.render_template()
        # print('\n'.join([html_string_0, html_string_1]))
        file_name = 'report-{instance}-{time_string}.html'.format(instance=self.render_data['DBClusterId'],
                                                                  time_string=time.strftime('%Y%m%d%H%M%S',
                                                                                            time.localtime(
                                                                                                time.time())))
        with open('{}/{}'.format(out_dir, file_name), 'w') as f:
            f.write('\n'.join([html_string_0, html_string_1]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='''阿里云PolarDB集群每日慢查询报告小工具
Example：
获取所有地域PolarDB集群的每日慢查询报告
    python3 aliyun_get_polardb_slowlog.py --AccessKeyId ACCESSKEYID --AccessKeySecret ACCESSKEYSECRET --OutDir ./
    python3 aliyun_get_polardb_slowlog.py --AccessKeyId ACCESSKEYID --AccessKeySecret ACCESSKEYSECRET --OutDir ./ --Region all --Engine all
    支持指定 地域、存储引擎（MySQL, PostgreSQL, Oracle）、数据库实例ID PolarDB不支持到库级别的过滤（阿里云API没有该功能）
''', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--AccessKeyId", help="AccessKeyId 非必要参数")
    parser.add_argument("--AccessKeySecret", help="AccessKeySecret 非必要参数")
    parser.add_argument("--RoleName", help="RoleName 非必要参数")
    parser.add_argument("--OutDir", help="输出目录 必要参数 需要提前创建该目录")
    parser.add_argument("--AccountName", help="用户名 ShowOnly=Yes时为非必要参数")
    parser.add_argument("--AccountPassword", help="密码 ShowOnly=Yes时为非必要参数")
    parser.add_argument("--AccountDescription", help="账号描述 ShowOnly=Yes时为非必要参数")
    parser.add_argument("--Region", default='all', help='''指定地域 默认为all
all : 所有地域
cn-shanghai,cn-hangzhou : 上海和杭州 多个地域使用逗号分割
us-east-1 : 单个地域
因地域经常发化此处不罗列''')
    parser.add_argument("--Engine", default='all', help='''数据库类型 默认为all
    all : 所有数据库类型
    MySQL,PostgreSQL : 多个类型用逗号分割
    PostgreSQL : 单个类型
    支持的所有类型：MySQL,PostgreSQL,Oracle''')
    parser.add_argument("--DBClusterId", default='all', help='''数据库集群ID 默认为all
    rr-bp1d96998y68h5439,rm-bp1l20jmw5p587zl2 : 多个集群用逗号分割
    rr-bp1d96998y68h5439 : 单个集群''')

    args = parser.parse_args()

    common_region_ids = []
    db_engines = []

    if args.OutDir:
        params = {
            'AccessKeyId': args.AccessKeyId,
            'AccessKeySecret': args.AccessKeySecret,
            'RoleName': args.RoleName,
        }
        api = Custom()
        api.get_config(**params)

        if args.Region == 'all':
            common_region_ids = api.get_describe_regions()
        elif len(args.Region.split(',')):
            common_region_ids = args.Region.split(',')

        if args.Engine == 'all':
            db_engines = ['MySQL', 'PostgreSQL', 'Oracle']
        elif len(args.Engine.split(',')):
            db_engines = args.Engine.split(',')


        main_kwargs = {
            'common_region_ids': common_region_ids,
            'db_engines': db_engines,
            'filter_instance': False if args.DBClusterId == 'all' else True,
            'DBClusterIds': args.DBClusterId.split(','),
            'out_dir': args.OutDir,
        }

        api.start_up(**main_kwargs)
