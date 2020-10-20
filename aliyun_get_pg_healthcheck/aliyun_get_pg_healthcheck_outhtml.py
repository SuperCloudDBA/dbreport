# -*- coding: utf-8 -*-
"""
输出目标 PostgreSQL 数据库健康报告
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

class GetReport:
    """
    渲染数据库报告到前端
    """

    def __init__(self, **kwargs):
        self.render_data = kwargs

    def render_template(self):
        template_data = """
       <div class="row">
        {% for _data in data %}
        <div class="col-sm-3">
            <div class="accordion" id="accordionExample{{ _data.type }}">
                <a class="nav-link" href="#{{ _data.type }}">
                    <div class="card">
                        <div class="card-header" id="heading{{ _data.type }}">
                            <h6 class="font-weight-lighter ">{{ _data.desc }}</h6>
                            <h2 class="mb-0">
                                <button class="btn btn-link btn-block text-left text-decoration-none" type="button"
                                        data-toggle="collapse"
                                        data-target="#collapse2" aria-expanded="true" aria-controls="collapse2">

                                    <div class="row">

                                        <svg t="1595576703545" class="icon" viewBox="0 0 1024 1024" version="1.1"
                                             xmlns="http://www.w3.org/2000/svg" p-id="9859" width="60" height="60">
                                            <path d="M829.68893465 359.94375777a349.44 349.44 0 0 1 33.71485133 132.37038944 32 32 0 0 0 63.80931593-3.62038672 413.76 413.76 0 0 0-40.05052808-156.35545145 32 32 0 0 0-6.10940259-8.82469263 32 32 0 0 0-51.36423659 36.43014136zM783.52900398 272.60192816A32 32 0 0 0 806.15642097 263.09841302a32 32 0 0 0 6.7882251-10.40861182 37.12 37.12 0 0 0 2.71529004-12.21880518 36.8 36.8 0 0 0-2.71529004-12.21880517 30.08 30.08 0 0 0-17.19683692-17.19683692 28.8 28.8 0 0 0-24.43761035 0A32 32 0 0 0 760.90158698 217.84357903a32 32 0 0 0 22.627417 54.75834913z"
                                                  fill="#f59207" p-id="9860"></path>
                                            <path d="M172.58874503 851.41125497l45.254834-45.254834A416 416 0 0 0 913.86292588 619.70650491a32 32 0 1 0-61.7728484-16.51801441A352 352 0 0 1 263.09841302 760.90158698l45.254834-45.254834a288 288 0 0 1 0-407.29350596l-45.254834-45.254834a352 352 0 0 1 400.73155504-69.01362184 32 32 0 1 0 27.37917456-57.69991335A416 416 0 0 0 217.84357903 217.84357903l-45.254834-45.254834A480 480 0 0 0 172.58874503 851.41125497z"
                                                  fill="#08b3f4" p-id="9861"></path>
                                        </svg>
                                    </div>

                                </button>
                            </h2>
                        </div>
                    </div>
                </a>
                </div>
            </div>
        {% endfor %}
                </div>
        {% for _data in data %}
            <div class="new_container">
                            <dl class="row">
                                <dt class="col-sm-3">{{ _data.desc }}</dt>
                            </dl>
                    <table
  id="{{ _data.type }}"
  data-toggle="table"
  data-height="460"
  data-ajax="ajaxRequest{{ _data.type}}"
  data-search="false"
  data-side-pagination="server"
  data-pagination="true">
  <thead>
    <tr>
    {% for field in _data.fields %}
        <th scope="col" data-field={{ field }}>{{ field }}</th>
    {% endfor %}
    </tr>
  </thead>
</table>
<script>
  // your custom ajax request here
  function ajaxRequest{{ _data.type}}(params) {
    res = {{ _data }}
    params.success(res)
  }
</script>

         </div>
        {% endfor %}


</div>
<!-- Optional JavaScript -->
<!-- jQuery first, then Popper.js, then Bootstrap JS -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.5.1/jquery.min.js" integrity="sha512-bLT0Qm9VnAYZDflyKcBaQ2gg0hSYNQrJ8RilYldYQ1FxQYoCLtUjuuRuZo+fjqhx/qtq/1itJ0C2ejDxltZVFg==" crossorigin="anonymous"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.7/umd/popper.min.js" integrity="sha384-UO2eT0CpHqdSJQ6hJty5KVphtPhzWj9WO1clHTMGa3JDZwrnQq4sF86dIHNDz0W1" crossorigin="anonymous"></script>
    <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.min.js" integrity="sha384-JjSmVgyd0p3pXB1rRibZUAYoIIy6OrQ6VrjIEaFf/nJGzIxFDsf4x0xIM+B07jRM" crossorigin="anonymous"></script>
    <script src="https://unpkg.com/bootstrap-table@1.17.1/dist/bootstrap-table.min.js"></script>

</body>
</html>
"""

        template = Template(template_data)
        return template.render(**self.render_data)

    def maker(self, host, out_dir):
        # 因为CSS中存在{{因此不能放在template_data中渲染
        html_string_head = """<!doctype html>
<html lang="en">
<head>
    <!-- Required meta tags -->
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">

    <!-- Bootstrap CSS -->
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css" integrity="sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T" crossorigin="anonymous">
    <link rel="stylesheet" href="https://use.fontawesome.com/releases/v5.6.3/css/all.css" integrity="sha384-UHRtZLI+pbxtHCWp1t77Bi1L4ZtiqrqD80Kn4Z8NTSRyMA2Fd33n5dQ8lWUE00s/" crossorigin="anonymous">
    <link rel="stylesheet" href="https://unpkg.com/bootstrap-table@1.17.1/dist/bootstrap-table.min.css">
    <title>数据库报告</title>
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
        <h3 class="title text-center">阿里云RDS For PostgreSQL 库表统计报告</h3>
        <div class="row text-muted">
            <div class="col-md-12 text-center">报告时间： {0} </div>
        </div>
        <p class=summary>
            尊敬的客户您好，本文档为实时数据库报告，通过本报告能够反映当前数据库的情况。本文档的一切解释权归驻云科技有限公司所有，如有问题，请联系您的客户技术经理或服务工程师咨询</p>
    </div>
            <a href="#" style="position:fixed;right:0;bottom:0">
<svg t="1597730333148" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="10565" width="64" height="64"><path d="M528 67.5l-16-16.7-15.9 16.7c-7.3 7.7-179.9 190.6-179.9 420.8 0 112 40 210.1 73.5 272.7l6.2 11.6H627l5.9-13c3.1-6.8 75-167.8 75-271.3 0-230.2-172.6-413.1-179.9-420.8z m-16 48.8c19 22.9 51.9 66.1 82.3 122.5H429.8c30.3-56.4 63.3-99.6 82.2-122.5z m86.3 612.2H422.5c-25.7-50.6-62.2-140.1-62.2-240.2 0-75 20.8-145.5 47.7-205.4h208.2c26.8 59.9 47.6 130.3 47.6 205.4-0.1 78.3-48.7 200.4-65.5 240.2z" fill="#1E59E4" p-id="10566"></path><path d="M834.7 623.9H643.3l6.7-27.3c9.1-37 13.7-73.4 13.7-108.2 0-44.8-7.7-92-22.9-140.3l-17-54 49.1 28.3c99.8 57.6 161.8 164.7 161.8 279.5v22z m-135.9-44.2h90.9c-5.7-71-38.8-137.2-91.3-184.6 6.3 31.7 9.4 62.9 9.4 93.2 0.1 29.7-3 60.3-9 91.4zM380.1 623.9H189.3v-22.1c0-114.8 62-221.9 161.8-279.5l49.1-28.3-17 54c-15.2 48.3-22.9 95.5-22.9 140.3 0 34.5 4.5 71 13.4 108.4l6.4 27.2z m-145.8-44.2H325c-5.9-31.3-8.8-61.9-8.8-91.4 0-30.3 3.2-61.5 9.4-93.2-52.5 47.5-85.6 113.6-91.3 184.6zM512 529.5c-45 0-81.6-36.6-81.6-81.6s36.6-81.6 81.6-81.6 81.6 36.6 81.6 81.6-36.6 81.6-81.6 81.6z m0-119c-20.7 0-37.5 16.8-37.5 37.5s16.8 37.5 37.5 37.5 37.5-16.8 37.5-37.5-16.8-37.5-37.5-37.5z" fill="#1E59E4" p-id="10567"></path><path d="M512 999.7l-20.3-20.3c-28.8-28.6-68.3-67.9-68.3-111.6 0-48.9 39.8-88.6 88.6-88.6 48.9 0 88.6 39.8 88.6 88.6 0 43.6-24.4 67.9-64.8 108.2L512 999.7z m0-176.4c-24.5 0-44.5 20-44.5 44.5 0 21.5 23.8 48.4 44.5 69.5 33.6-33.7 44.4-47 44.4-69.5 0.1-24.6-19.9-44.5-44.4-44.5z" fill="#FF5A06" p-id="10568"></path></svg></a>
        """.format(time.strftime('%Y年%m月%d日 %H:%M:%S'.encode('unicode_escape').decode('utf8'),time.localtime(time.time())).encode('utf-8').decode('unicode_escape'))
        html_string_2 = self.render_template()
        # print('\n'.join([html_string_0, html_string_1]))
        file_name = 'report-{host}-{time_string}.html'.format(host=host,
            time_string=time.strftime('%Y%m%d%H%M%S', time.localtime(time.time())))
        path = '{}/{}'.format(out_dir,time.strftime('%Y%m%d', time.localtime(time.time())))
        if not os.path.exists(path):
            os.mkdir(path)
        with open('{}/{}/{}'.format(out_dir,time.strftime('%Y%m%d', time.localtime(time.time())), file_name), 'w', encoding='utf-8') as f:
            f.write('\n'.join([html_string_head, html_string_1, html_string_2]))

