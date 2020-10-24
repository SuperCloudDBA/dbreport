# -*- coding: utf-8 -*-
"""
auth: Booboowei
desc: MySQL 5.7 安全基线检查
根据以下文章进行整理学习：
* [CIS Oracle MySQL Community Server 5.7 Benchmark v1.0.0 - 12-29-2015](http://benchmarks.cisecurity.org)
* 文档《CIS Oracle MySQL Community Server 5.7 Benchmark》为建立MySQL Community Server的安全配置姿态提供了规范性指导。
* CIS（互联网安全中心）是美国一家非盈利技术组织，主要是制定一些系统安全基线。
* 指南针对运行在ubuntulinux14.04上的MySQL社区服务器5.7进行了测试，但也适用于其他Linux发行版。
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


cis_mysql_57_benchmark = [
    {
        "name": "操作系统级配置",
        "v_name": "OperatingSystemLevelConfiguration",
        "value": [
            {
                "check_name": "",  # 基线名
                "is_scored": "1",  # 是否计分 1 积分 0 不计分
                "applicability": "",  # 基础安全措施、纵深防御措施
                "Description": "",  # 描述
                "rationale": "",  # 理论基础
                "audit": "",  # 检查算法
                "remediation": "",  # 修复方法
                "impact": None,  # 影响
                "default_value": None,  # 默认值
                "references": """""",  # 链接
                "check_func": "",  # 检查函数名
            }
        ]
    },
    {"name": "安装和规划", "v_name": "InstallationandPlanning", "value": []},
    {"name": "文件系统权限", "v_name": "FileSystemPermissions", "value": []},
    {"name": "总则", "v_name": "General", "value": []},
    {"name": "MySQL权限", "v_name": "MySQLPermissions", "value": []},
    {"name": "审核和记录", "v_name": "AuditingAndLogging", "value": []},
    {"name": "身份验证", "v_name": "Authentication", "value": []},
    {"name": "网络", "v_name": "Network", "value": []},
    {"name": "复制", "v_name": "Replication", "value": []},
]

# 操作系统级配置
OperatingSystemLevelConfiguration = {
    "name": "操作系统级配置",
    "value": [
        {
            "check_name": "将数据库放在非系统分区上",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "Description": "主机操作系统应该为不同的目的包含不同的文件系统分区。一组文件系统通常称为“系统分区”，通常为主机系统/应用程序操作保留。另一组文件系统通常称为“非系统分区”，这些位置通常是为存储数据而保留的。",
            "rationale": "主机操作系统应该为不同的目的包含不同的文件系统分区。一组文件系统通常称为“系统分区”，通常为主机系统/应用程序操作保留。另一组文件系统通常称为“非系统分区”，这些位置通常是为存储数据而保留的。",
            "audit": """执行以下命令：
show variables where variable_name = 'datadir';
df -h <datadir Value>
df命令的结果不应该包括 ('/'), "/var", or "/usr" 的目录。
""",
            "remediation": """请执行以下步骤修正此设置：
1.为MySQL数据选择一个非系统分区的新位置
2.使用命令停止mysqld，比如：service mysql Stop
3.使用命令复制数据：cp-rp<datadir Value><new location>
4.将datadir位置设置为MySQL配置文件中的新位置
5.使用命令启动mysqld，比如：service mysql start

注意：在某些Linux发行版上，您可能需要另外修改apparmor设置。例如，在Ubuntu14.04.1系统上，编辑文件/etc/apparmor.d/usr.sbin.mysqld公司因此datadir访问是适当的。""",
            "impact": "将数据库移动到非系统分区可能很困难，这取决于设置操作系统时是否只有一个分区，以及是否有额外的可用存储空间。",
            "default_value": None,
            "references": None,
            "check_func": check_mysql_datadir,
        },
        {
            "check_name": "使用MySQL守护程序/服务的最低特权专用帐户",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "Description": "与安装在主机上的任何服务一样，它可以提供自己的用户上下文。为服务提供一个专用的用户可以在更大的主机上下文中精确地约束服务。",
            "rationale": "利用MySQL的最低权限帐户执行as可能会减少MySQL固有漏洞的影响。受限帐户将无法访问与MySQL无关的资源，例如操作系统配置。",
            "audit": """执行以下命令：
ps -ef | egrep "^mysql.*$"
如果未返回任何行，则不得分
""",
            "remediation": "创建一个只用于运行MySQL和直接相关进程的用户。此用户不得具有系统的管理权限。",
            "impact": None,
            "default_value": None,
            "references": """1. http://dev.mysql.com/doc/refman/5.7/en/changing-mysql-user.html 
2. http://dev.mysql.com/doc/refman/5.7/en/server-options.html#option_mysqld_user""",
            "check_func": check_mysql_user,
        },
        {
            "check_name": "禁用MySQL命令历史记录",
            "is_scored": "1",
            "applicability": "纵深防御措施",
            "Description": "在Linux/UNIX上，MySQL客户机将交互执行的语句记录到历史记录中文件。默认情况下，此文件在用户的主目录中命名为.mysql_history。在MySQL客户机应用程序中运行的大多数交互式命令都保存在历史文件中。应禁用MySQL命令历史记录。",
            "rationale": "禁用MySQL命令历史记录可以降低暴露敏感信息（如密码和加密密钥）的概率。",
            "audit": """执行以下命令：
find /home -name ".mysql_history"
如果没有文件返回则得分，否则对于返回的每个文件，确定该文件是否符号链接到/dev/null，如果是则得分，否则不得分
""",
            "remediation": """请执行以下步骤修正此设置：
1. 删除 .mysql_history（如果存在）。
2. 使用以下任一技术防止再次创建：
2.1 将 MYSQL_HISTFILE 环境变量设置为 /dev/null。这需要放在shell的启动脚本中。
2.2 创建 $HOME/.mysql_history 作为 /dev/null的软连接 。
> ln -s /dev/null $HOME/.mysql_history
""",
            "impact": None,
            "default_value": "默认情况下，MySQL命令历史文件位于$HOME/.MySQL_history中。",
            "references": """1. http://dev.mysql.com/doc/refman/5.7/en/mysql-logging.html 
2. http://bugs.mysql.com/bug.php?id=72158
""",
            "check_func": "disable_mysql_command_history",
        },
        {
            "check_name": "验证MYSQL_PWD环境变量是否未使用",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "Description": "MySQL可以从名为MySQL_PWD的环境变量中读取默认数据库密码。",
            "rationale": "MYSQL_PWD环境变量的使用意味着MYSQL凭证的明文存储。避免这种情况可能会增加对MySQL凭证保密性的保证。",
            "audit": """执行以下命令：
grep MYSQL_PWD/proc/*/environ
如果未返回任何行，则得分；否则代表设置了参数 MYSQL_PWD 则不得分。
""",
            "remediation": "检查哪些用户和/或脚本正在设置MYSQL_PWD，并将其更改为使用更安全的方法。",
            "impact": None,
            "default_value": None,
            "references": """1. http://dev.mysql.com/doc/refman/5.7/en/environment-variables.html
2. https://blogs.oracle.com/myoraclediary/entry/how_to_check_environment_variables""",
            "check_func": check_mysql_pwd_from_proc,
        },
        {
            "check_name": "禁用交互式登录",
            "is_scored": "1",
            "applicability": "纵深防御措施",
            "Description": "创建后，MySQL用户可以交互访问操作系统，这意味着MySQL用户可以像其他用户一样登录主机。",
            "rationale": "阻止MySQL用户以交互方式登录可能会减少MySQL帐户受损的影响。此外，访问MySQL服务器所在的操作系统需要用户自己的帐户，这也需要更多的责任。MySQL用户的交互访问是不必要的，应该禁用。",
            "audit": """执行以下命令：
getent passwd mysql | egrep "^.*[\/bin\/false|\/sbin\/nologin]$"
如果未返回任何行，则不得分
""",
            "remediation": """请执行以下步骤进行修复：（在终端中执行以下命令之一）
usermod -s /bin/false 
usermod -s /sbin/nologin
""",
            "impact": """此设置将阻止MySQL管理员使用MySQL用户以交互方式登录到操作系统。""",
            "default_value": None,
            "references": None,
            "check_func": check_mysql_login,
        },
        {
            "check_name": "验证“MYSQL_PWD”未在用户配置文件中设置",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "Description": "MySQL可以从名为MySQL_PWD的环境变量中读取默认数据库密码。",
            "rationale": "MYSQL_PWD环境变量的使用意味着MYSQL凭证的明文存储。避免这种情况可能会增加对MySQL凭证保密性的保证。",
            "audit": """执行以下命令：
grep MYSQL_PWD /home/*/.{bashrc,profile,bash_profile}
如果未返回任何行，则不得分
""",
            "remediation": "检查哪些用户和/或脚本正在设置MYSQL_PWD，并将其更改为使用更安全的方法。",
            "impact": None,
            "default_value": None,
            "references": """1. http://dev.mysql.com/doc/refman/5.7/en/environment-variables.html
2. https://blogs.oracle.com/myoraclediary/entry/how_to_check_environment_variables""",
            "check_func": check_mysql_pwd_from_file,
        },
    ],

}

# 安装和规划
InstallationandPlanning = {
    "name": "安装和规划",
    "value": [  ## 备份和灾难恢复
        {
            "check_name": "备份策略到位",
            "is_scored": "0",
            "applicability": "基础安全措施",
            "Description": "应制定备份策略。",
            "rationale": "备份MySQL数据库将有助于确保发生事故时的数据可用性。",
            "audit": """执行以下命令：crontab -l 检查是否有备份计划。""",
            "remediation": "创建备份策略和备份计划。",
            "impact": "没有备份，可能很难从事故中恢复",
            "default_value": None,
            "references": None,
            "check_func": check_mysql_backup_policy,
        }, {
            "check_name": "验证备份是否良好",
            "is_scored": "0",
            "applicability": "基础安全措施",
            "Description": "备份应定期进行有效性验证",
            "rationale": "验证备份是否正确进行将有助于确保发生事故时的数据可用性。",
            "audit": """检查备份验证测试的报告。备份验证需要在测试环境中将数据进行恢复后应用测试得到验证报告。""",
            "remediation": "实施常规备份检查并记录每个检查。",
            "impact": "如果没有经过良好测试的备份，那么如果备份的过程包含错误或不包含所有必需的数据时，数据可能很难从事故中恢复。",
            "default_value": None,
            "references": None,
            "check_func": check_mysql_backups_good,
        }, {
            "check_name": "安全备份凭据",
            "is_scored": "0",
            "applicability": "基础安全措施",
            "Description": "密码、证书和任何其他凭据都应受到保护。",
            "rationale": "用于备份的用户拥有所有特权，因此该用户的凭据应受到保护。",
            "audit": """检查包含密码或ssl密钥的文件的权限。""",
            "remediation": "更改文件权限。",
            "impact": "如果备份凭据没有得到适当的保护，则可能会滥用它们以获取访问服务器。备份用户需要一个具有许多特权的帐户，因此攻击者可以（几乎）完全访问服务器。",
            "default_value": None,
            "references": None,
            "check_func": check_mysql_backup_credentials,
        }, {
            "check_name": "备份应妥善保护",
            "is_scored": "0",
            "applicability": "基础安全措施",
            "Description": "备份文件将包含数据库中的所有数据。应该使用文件系统权限或加密来防止未经授权的用户访问备份数据。",
            "rationale": "备份应被视为敏感信息。",
            "audit": """检查谁有权访问备份文件。
            文件是否可对于所有用户可读（例如rw-r--r-）  
                它们存储在所有用户可读的目录中吗？  
            MySQL或备份组是否特定？  
                如果不是，则文件和目录不能设置为组可读  
            备份是否存储在异地？  
                谁有权访问备份？  
            备份是否加密？  
                加密密钥存储在哪里？  
                加密密钥是否包含可猜测的密码？
            """,
            "remediation": "实现加密或使用文件系统权限",
            "impact": "如果未经授权的用户可以访问备份，则他们可以访问其中的所有数据数据库。对于未加密的备份和加密的备份，这是正确的。  加密密钥与备份一起存储。",
            "default_value": None,
            "references": None,
            "check_func": check_mysql_backup_secured,
        }, {
            "check_name": "时间点恢复",
            "is_scored": "0",
            "applicability": "纵深防御措施",
            "Description": "使用二进制日志，可以实现时间点恢复。这样就可以恢复上一次完整备份和时间点之间的更改。启用二进制日志是不够的，应该创建一个还原过程，并且必须经过测试。",
            "rationale": "这样可以减少丢失的信息量。",
            "audit": """检查二进制日志是否已启用以及是否有还原过程。""",
            "remediation": "启用binlog并创建和测试还原过程。 ",
            "impact": "如果不进行时间点恢复，则在上次备份和备份之间存储的数据灾难时期可能无法恢复。",
            "default_value": None,
            "references": None,
            "check_func": check_mysql_backup_point_in_time,
        }, {
            "check_name": "灾难恢复计划",
            "is_scored": "0",
            "applicability": "基础安全措施",
            "Description": "xx",
            "rationale": "xx",
            "audit": """xx""",
            "remediation": "创建备份策略和备份计划。",
            "impact": "xx",
            "default_value": None,
            "references": None,
            "check_func": check_mysql_datadir,
        }, {
            "check_name": "配置和相关文件的备份",
            "is_scored": "0",
            "applicability": "基础安全措施",
            "Description": "xx",
            "rationale": "xx",
            "audit": """xx""",
            "remediation": "创建备份策略和备份计划。",
            "impact": "xx",
            "default_value": None,
            "references": None,
            "check_func": check_mysql_datadir,
        },  ## 备份和灾难恢复
        {
            "check_name": "专用机器运行MySQL",
            "is_scored": "0",
            "applicability": "基础安全措施",
            "Description": "xx",
            "rationale": "xx",
            "audit": """xx""",
            "remediation": "创建备份策略和备份计划。",
            "impact": "xx",
            "default_value": None,
            "references": None,
            "check_func": check_mysql_datadir,
        }, {
            "check_name": "不要在命令行中指定密码",
            "is_scored": "0",
            "applicability": "基础安全措施",
            "Description": "xx",
            "rationale": "xx",
            "audit": """xx""",
            "remediation": "创建备份策略和备份计划。",
            "impact": "xx",
            "default_value": None,
            "references": None,
            "check_func": check_mysql_datadir,
        }, {
            "check_name": "不重复使用用户名",
            "is_scored": "0",
            "applicability": "基础安全措施",
            "Description": "xx",
            "rationale": "xx",
            "audit": """xx""",
            "remediation": "创建备份策略和备份计划。",
            "impact": "xx",
            "default_value": None,
            "references": None,
            "check_func": check_mysql_datadir,
        }, {
            "check_name": "不要使用默认或非MySQL特定的加密密钥",
            "is_scored": "0",
            "applicability": "纵深防御措施",
            "Description": "xx",
            "rationale": "xx",
            "audit": """xx""",
            "remediation": "创建备份策略和备份计划。",
            "impact": "xx",
            "default_value": None,
            "references": None,
            "check_func": check_mysql_datadir,
        }, {
            "check_name": "为特定用户设置密码过期策略",
            "is_scored": "0",
            "applicability": "基础安全措施",
            "Description": "xx",
            "rationale": "xx",
            "audit": """xx""",
            "remediation": "创建备份策略和备份计划。",
            "impact": "xx",
            "default_value": None,
            "references": None,
            "check_func": check_mysql_datadir,
        },
    ]
}
