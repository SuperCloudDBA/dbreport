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
import os

# 3rd-part Modules
import pymysql
import xlsxwriter
import argparse
from jinja2 import Template

now_date = time.strftime('%Y%m%d', time.localtime())

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


class Outputexcel():
    def __init__(self, **kwargs):
        """
        :param kwargs: {dir_name: "dir_name", report_name: "report_name"}
        """
        self.file_name = os.path.join(kwargs['dir_name'], '{}_{}.xlsx'.format(kwargs['report_name'], now_date))
        self.workbook = xlsxwriter.Workbook(self.file_name)

    def write_file_column(self, worksheet, fields):
        top = self.workbook.add_format(
            {'border': 1, 'align': 'center', 'bg_color': '#FF9966', 'font_size': 10, 'bold': True})  # 设置单元格格式
        j = 0
        for i in fields:
            worksheet.write(0, j, i, top)
            j += 1

    def add_sheet(self, sheet_name, fields, list_keys, lines):
        print(sheet_name)
        self.workbook.add_format({'border': 1, 'align': 'center', 'font_size': 10})
        worksheet = self.workbook.add_worksheet(sheet_name)

        for _c in range(len(list_keys)):
            worksheet.set_column('{0}:{0}'.format(chr(_c + ord('A'))), 30)
        self.write_file_column(worksheet, fields)
        row = 1
        for data in lines:
            # print(data)
            for col, filed in enumerate(data):
                # print(col,filed)
                worksheet.write(row, col, filed)
            row += 1

    def write_close(self):
        self.workbook.close()


# cis_mysql_57_benchmark = [
#     {
#         "name": "操作系统级配置",
#         "v_name": "OperatingSystemLevelConfiguration",
#         "value": [
#             {
#                 "check_name": "",  # 基线名
#                 "is_scored": "1",  # 是否计分 1 积分 0 不计分
#                 "applicability": "",  # 基础安全措施、纵深防御措施
#                 "description": "",  # 描述
#                 "rationale": "",  # 理论基础
#                 "audit": "",  # 检查算法
#                 "remediation": "",  # 修复方法
#                 "impact": None,  # 影响
#                 "default_value": None,  # 默认值
#                 "references": """""",  # 链接
#                 "check_func": """",  # 检查函数名
#             }
#         ]
#     },
#     {"name": "安装和规划", "v_name": "InstallationandPlanning", "value": []},
#     {"name": "文件系统权限", "v_name": "FileSystemPermissions", "value": []},
#     {"name": "总则", "v_name": "General", "value": []},
#     {"name": "MySQL权限", "v_name": "MySQLPermissions", "value": []},
#     {"name": "审核和记录", "v_name": "AuditingAndLogging", "value": []},
#     {"name": "身份验证", "v_name": "Authentication", "value": []},
#     {"name": "网络", "v_name": "Network", "value": []},
#     {"name": "复制", "v_name": "Replication", "value": []},
# ]

# 操作系统级配置
OperatingSystemLevelConfiguration = {
    "name": "操作系统级配置",
    "value": [
        {
            "check_name": "将数据库放在非系统分区上",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "主机操作系统应该为不同的目的包含不同的文件系统分区。一组文件系统通常称为“系统分区”，通常为主机系统/应用程序操作保留。另一组文件系统通常称为“非系统分区”，这些位置通常是为存储数据而保留的。",
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
            "check_func": "check_mysql_on_non_system_partitions",
        },
        {
            "check_name": "使用MySQL守护程序/服务的最低特权专用帐户",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "与安装在主机上的任何服务一样，它可以提供自己的用户上下文。为服务提供一个专用的用户可以在更大的主机上下文中精确地约束服务。",
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
            "check_func": "check_mysql_user",
        },
        {
            "check_name": "禁用MySQL命令历史记录",
            "is_scored": "1",
            "applicability": "纵深防御措施",
            "description": "在Linux/UNIX上，MySQL客户机将交互执行的语句记录到历史记录中文件。默认情况下，此文件在用户的主目录中命名为.mysql_history。在MySQL客户机应用程序中运行的大多数交互式命令都保存在历史文件中。应禁用MySQL命令历史记录。",
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
            "description": "MySQL可以从名为MySQL_PWD的环境变量中读取默认数据库密码。",
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
            "check_func": "check_mysql_pwd_from_proc",
        },
        {
            "check_name": "禁用交互式登录",
            "is_scored": "1",
            "applicability": "纵深防御措施",
            "description": "创建后，MySQL用户可以交互访问操作系统，这意味着MySQL用户可以像其他用户一样登录主机。",
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
            "check_func": "check_mysql_login",
        },
        {
            "check_name": "验证“MYSQL_PWD”未在用户配置文件中设置",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "MySQL可以从名为MySQL_PWD的环境变量中读取默认数据库密码。",
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
            "check_func": "check_mysql_pwd_from_file",
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
            "description": "应制定备份策略。",
            "rationale": "备份MySQL数据库将有助于确保发生事故时的数据可用性。",
            "audit": """执行以下命令：crontab -l 检查是否有备份计划。""",
            "remediation": "创建备份策略和备份计划。",
            "impact": "没有备份，可能很难从事故中恢复",
            "default_value": None,
            "references": None,
            "check_func": "check_mysql_backup_policy",
        }, {
            "check_name": "验证备份是否良好",
            "is_scored": "0",
            "applicability": "基础安全措施",
            "description": "备份应定期进行有效性验证",
            "rationale": "验证备份是否正确进行将有助于确保发生事故时的数据可用性。",
            "audit": """检查备份验证测试的报告。备份验证需要在测试环境中将数据进行恢复后应用测试得到验证报告。""",
            "remediation": "实施常规备份检查并记录每个检查。",
            "impact": "如果没有经过良好测试的备份，那么如果备份的过程包含错误或不包含所有必需的数据时，数据可能很难从事故中恢复。",
            "default_value": None,
            "references": None,
            "check_func": "check_mysql_backups_good",
        }, {
            "check_name": "安全备份凭据",
            "is_scored": "0",
            "applicability": "基础安全措施",
            "description": "密码、证书和任何其他凭据都应受到保护。",
            "rationale": "用于备份的用户拥有所有特权，因此该用户的凭据应受到保护。",
            "audit": """检查包含密码或ssl密钥的文件的权限。""",
            "remediation": "更改文件权限。",
            "impact": "如果备份凭据没有得到适当的保护，则可能会滥用它们以获取访问服务器。备份用户需要一个具有许多特权的帐户，因此攻击者可以（几乎）完全访问服务器。",
            "default_value": None,
            "references": None,
            "check_func": "check_mysql_backup_credentials",
        }, {
            "check_name": "备份应妥善保护",
            "is_scored": "0",
            "applicability": "基础安全措施",
            "description": "备份文件将包含数据库中的所有数据。应该使用文件系统权限或加密来防止未经授权的用户访问备份数据。",
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
            "check_func": "check_mysql_backup_secured",
        }, {
            "check_name": "时间点恢复",
            "is_scored": "0",
            "applicability": "纵深防御措施",
            "description": "使用二进制日志，可以实现时间点恢复。这样就可以恢复上一次完整备份和时间点之间的更改。启用二进制日志是不够的，应该创建一个还原过程，并且必须经过测试。",
            "rationale": "这样可以减少丢失的信息量。",
            "audit": """检查二进制日志是否已启用以及是否有还原过程。""",
            "remediation": "启用binlog并创建和测试还原过程。 ",
            "impact": "如果不进行时间点恢复，则在上次备份和备份之间存储的数据灾难时期可能无法恢复。",
            "default_value": None,
            "references": None,
            "check_func": "check_mysql_backup_point_in_time",
        }, {
            "check_name": "灾难恢复计划",
            "is_scored": "0",
            "applicability": "基础安全措施",
            "description": """应该创建灾难恢复计划。
1. 可以使用其他数据中心的备库或异地备份；
2. 明确有关恢复所需时间点
3. 明确恢复服务器的存储容量""",
            "rationale": "应该计划灾难恢复",
            "audit": """检查是否有灾难恢复计划。""",
            "remediation": "制定灾难恢复计划。",
            "impact": "没有经过良好测试的灾难恢复计划，可能无法及时恢复。",
            "default_value": None,
            "references": None,
            "check_func": "check_mysql_disaster_recovery_plan",
        }, {
            "check_name": "配置和相关文件的备份",
            "is_scored": "0",
            "applicability": "基础安全措施",
            "description": """备份中应包含以下文件：
1. 配置文件（my.cn f和随附的文件)
2. SSL文件（证书，密钥）  
3. 用户定义函数（UDF）  
4. 定制的源代码""",
            "rationale": "需要这些文件才能完全还原实例",
            "audit": """检查这些文件是否已使用并保存在备份中。""",
            "remediation": "将这些文件添加到备份中。",
            "impact": "如果没有完整的备份，可能无法完全恢复。",
            "default_value": None,
            "references": None,
            "check_func": "check_mysql_backup_of_configuration_and_related_files",
        },
        {
            "check_name": "专用机器运行MySQL",
            "is_scored": "0",
            "applicability": "基础安全措施",
            "description": """建议在专用服务器上安装MySQL Server软件。该架构将提供灵活性，因为可以将数据库服务器放置在单独的区域，仅允许来自特定主机和特定协议的访问。""",
            "rationale": """在仅具有底层操作系统的服务器上，MySQL服务器软件，以及可能额外提供的任何安全性或操作工具已安装，将攻击面减少。""",
            "audit": """确认没有为基础操作系统启用其他角色，并且没有与MySQL服务器正常运行无关的其他应用程序或服务已安装软件。""",
            "remediation": "删除多余的应用程序或服务和/或删除不必要的角色  基础操作系统。",
            "impact": "删除必须注意正确操作，仅删除不需的应用程序或服务，而不会删除操作系统相关的程序或文件。",
            "default_value": None,
            "references": None,
            "check_func": "check_mysql_password_in_command_line",
        }, {
            "check_name": "不要在命令行中指定密码",
            "is_scored": "0",
            "applicability": "基础安全措施",
            "description": "在命令行上执行命令时，例如: mysql -u admin –p password ，该密码可能会在用户的Shell程序/命令历史记录中被记录。",
            "rationale": "如果密码在进程列表或用户的shell程序/命令历史记录中可见，则表示攻击者 将能够使用被盗的凭据访问MySQL数据库",
            "audit": """如果密码可见，请检查进程、任务列表、Shell程序、命令历史记录。""",
            "remediation": """1. 使用-p不带密码交互式输入；
2. 使用正确安全的.my.cnf文件；
3. 使用mysql_config_editor将身份验证信息以加密格式存储在 .mylogin.cnf文件中""",
            "impact": """根据所选的补救措施，可能需要执行其他步骤，例如： 
1. 出现提示时输入密码；
2. 确保.my.cnf上的文件权限受到限制，但用户可以访问；
3. 使用mysql_config_editor加密身份验证凭据.mylogin.cnf。 
此外，并非所有脚本/应用程序都可以使用.mylogin.cnf。
参考文献：  
    1. http://dev.mysql.com/doc/refman/5.7/en/mysql-config-editor.html  
    2. http://dev.mysql.com/doc/refman/5.7/en/password-security-user.html 
""",
            "default_value": None,
            "references": None,
            "check_func": "check_mysql_datadir",
        }, {
            "check_name": "不重复使用用户名",
            "is_scored": "0",
            "applicability": "基础安全措施",
            "description": "数据库用户帐户不应用于多个应用程序或用户。",
            "rationale": "在整个应用程序中使用唯一的数据库帐户将减少入侵的MySQL帐户。",
            "audit": """xx""",
            "remediation": "创建备份策略和备份计划。",
            "impact": "xx",
            "default_value": None,
            "references": None,
            "check_func": "check_mysql_reuse_usernames",
        }, {
            "check_name": "不要使用默认或非MySQL特定的加密密钥",
            "is_scored": "0",
            "applicability": "纵深防御措施",
            "description": "MySQL使用的SSL证书和密钥应仅用于MySQL，并且只能用于一个实例。 ",
            "rationale": "使用默认证书可以使攻击者冒充MySQL服务器。",
            "audit": """检查证书是否绑定到一个MySQL实例。""",
            "remediation": "为每个MySQL实例生成一个新的证书/密钥。",
            "impact": "如果密钥在多个系统上使用，那么一个系统的妥协将导致使用相同密钥的所有服务器的网络流量的危害。",
            "default_value": None,
            "references": None,
            "check_func": "check_mysql_cryptographic_Keys",
        }, {
            "check_name": "为特定用户设置密码过期策略",
            "is_scored": "0",
            "applicability": "基础安全措施",
            "description": "特定用户的密码到期为用户密码提供了唯一的时间限制。",
            "rationale": """允许与特定用户有关的其他安全因素来提供更多密码安全; 通过改变系统中的安全性需求和可用性要求来预先确定或组织
SELECT user, host, password_lifetime from mysql.user from mysql.user where  password_lifetime IS NULL; 
""",
            "audit": """返回当前使用全局设置default_password_life的所有用户，因此具有没有设置特定的用户密码有效期。""",
            "remediation": """使用审核过程中的用户和主机信息，为每个用户设置一个密码过期策略，例如 
ALTER USER 'jeffrey'@'localhost' PASSWORD EXPIRE INTERVAL 90 DAY;             
            """,
            "impact": "系统或组织的安全策略特有的其他密码安全因素也许被忽视了。",
            "default_value": None,
            "references": None,
            "check_func": "check_mysql_password_expiry_policy",
        },
    ]
}

# 文件系统权限
FileSystemPermissions = {
    "name": "文件系统权限",
    "v_name": "FileSystemPermissions",
    "value": [{
        "check_name": "确保datadir具有适当的权限",
        "is_scored": "1",
        "applicability": "基础安全措施",
        "description": "数据目录是MySQL数据库的位置。",
        "rationale": """限制这些对象的可访问性将保护机密性，完整性和安全性、MySQL日志的可用性。
如果允许MySQL用户以外的其他人从数据目录读取文件，他或她也许可以从mysql.user中读取数据包含密码的表。
此外，创建文件的能力可能导致拒绝服务，否则可能会允许某人通过手动访问特定数据创建具有视图定义的文件。""",
        "audit": """执行以下步骤来评估此建议：
1. 执行以下SQL语句以确定 datadir 的值
show variables where variable_name = 'datadir'; 
2. 在终端提示下执行以下命令
ls -l <datadir>/.. | egrep "^d[r|w|x]{3}------\s*.\s*mysql\s*mysql\s*\d*.*mysql" 
如果没有输出意味着发现问题。
""",
        "remediation": """在终端提示符下执行以下命令：
chmod 700 <datadir>  
chown mysql:mysql <datadir>  
    """,
        "impact": "",
        "default_value": None,
        "references": None,
        "check_func": "check_mysql_datadir_permissions",
    }, {
        "check_name": "确保log_bin_basename文件具有适当的权限",
        "is_scored": "1",
        "applicability": "基础安全措施",
        "description": """MySQL可以使用各种日志文件进行操作，每个日志文件用于不同的目的。这些是二进制日志，错误日志，慢查询日志，中继日志和常规日志。
        因为这些是文件在主机操作系统上，它们受制于主机，除MySQL用户外，其他用户也可以访问。""",
        "rationale": """限制这些对象的可访问性将保护机密性，完整性和安全性、MySQL日志的可用性。""",
        "audit": """执行以下步骤来评估此建议：
    1. 通过执行以下语句找到 log_bin_basename 值：show variables like 'log_bin_basename'; 
    2. 检查 log_bin_basename 的用户和组的权限为 mysql:mysql 执行权限为 660 
    """,
        "remediation": """对每个需要更正权限的日志文件位置执行以下命令： 
    chmod 660 <log file>  
    chown mysql:mysql <log file> 
    """,
        "impact": """更改日志文件的权限可能会影响使用日志文件适配器的监视工具。此外，慢速查询日志还可用于以下方面的性能分析：  
    应用程序开发人员。  
    如果中继日志和二进制日志文件的权限被意外更改为排除用于运行MySQL服务的用户帐户，则可能会中断复制。  
    二进制日志文件可用于时间点恢复，因此这也会影响备份，恢复和灾难恢复程序。""",
        "default_value": None,
        "references": None,
        "check_func": "check_mysql_log_bin_basename",
    }, {
        "check_name": "确保log_error具有适当的权限",
        "is_scored": "1",
        "applicability": "基础安全措施",
        "description": """MySQL可以使用各种日志文件进行操作，每个日志文件用于不同的目的。这些是二进制日志，错误日志，慢查询日志，中继日志和常规日志。
        因为这些是文件在主机操作系统上，它们受制于主机，除MySQL用户外，其他用户也可以访问。""",
        "rationale": """限制这些对象的可访问性将保护机密性，完整性和安全性、MySQL日志的可用性。""",
        "audit": """执行以下步骤来评估此建议：
    1. 通过执行以下语句找到 log_error 值：show variables like 'log_error'; 
    2. 检查 log_error 的用户和组的权限为 mysql:mysql 执行权限为 660 
    """,
        "remediation": """对每个需要更正权限的日志文件位置执行以下命令： 
    chmod 660 <log file>  
    chown mysql:mysql <log file> 
    """,
        "impact": """更改日志文件的权限可能会影响使用日志文件适配器的监视工具。此外，慢速查询日志还可用于以下方面的性能分析：  
    应用程序开发人员。  
    如果中继日志和二进制日志文件的权限被意外更改为排除用于运行MySQL服务的用户帐户，则可能会中断复制。  
    二进制日志文件可用于时间点恢复，因此这也会影响备份，恢复和灾难恢复程序。""",
        "default_value": None,
        "references": None,
        "check_func": "check_mysql_log_error",
    }, {
        "check_name": "确保slow_query_log具有适当的权限",
        "is_scored": "1",
        "applicability": "基础安全措施",
        "description": """MySQL可以使用各种日志文件进行操作，每个日志文件用于不同的目的。这些是二进制日志，错误日志，慢查询日志，中继日志和常规日志。
        因为这些是文件在主机操作系统上，它们受制于主机，除MySQL用户外，其他用户也可以访问。""",
        "rationale": """限制这些对象的可访问性将保护机密性，完整性和安全性、MySQL日志的可用性。""",
        "audit": """执行以下步骤来评估此建议：
    1. 通过执行以下语句找到 slow_query_log_file 值：show variables like 'slow_query_log_file'; 
    2. 检查 slow_query_log_file 的用户和组的权限为 mysql:mysql 执行权限为 660 
    """,
        "remediation": """对每个需要更正权限的日志文件位置执行以下命令： 
    chmod 660 <log file>  
    chown mysql:mysql <log file> 
    """,
        "impact": """更改日志文件的权限可能会影响使用日志文件适配器的监视工具。此外，慢速查询日志还可用于以下方面的性能分析：  
    应用程序开发人员。  
    如果中继日志和二进制日志文件的权限被意外更改为排除用于运行MySQL服务的用户帐户，则可能会中断复制。  
    二进制日志文件可用于时间点恢复，因此这也会影响备份，恢复和灾难恢复程序。""",
        "default_value": None,
        "references": None,
        "check_func": "check_mysql_slow_query_log",
    }, {
        "check_name": "确保relay_log_basename文件具有适当的权限",
        "is_scored": "1",
        "applicability": "基础安全措施",
        "description": """MySQL可以使用各种日志文件进行操作，每个日志文件用于不同的目的。这些是二进制日志，错误日志，慢查询日志，中继日志和常规日志。
    因为这些是文件在主机操作系统上，它们受制于主机，除MySQL用户外，其他用户也可以访问。""",
        "rationale": """限制这些对象的可访问性将保护机密性，完整性和安全性、MySQL日志的可用性。""",
        "audit": """执行以下步骤来评估此建议：
1. 通过执行以下语句找到 relay_log_basename 值：show variables like 'relay_log_basename'; 
2. 检查 relay_log_basename 的用户和组的权限为 mysql:mysql 执行权限为 660 
""",
        "remediation": """对每个需要更正权限的日志文件位置执行以下命令： 
chmod 660 <log file>  
chown mysql:mysql <log file> 
""",
        "impact": """更改日志文件的权限可能会影响使用日志文件适配器的监视工具。此外，慢速查询日志还可用于以下方面的性能分析：  
应用程序开发人员。  
如果中继日志和二进制日志文件的权限被意外更改为排除用于运行MySQL服务的用户帐户，则可能会中断复制。  
二进制日志文件可用于时间点恢复，因此这也会影响备份，恢复和灾难恢复程序。""",
        "default_value": None,
        "default_value": None,
        "references": None,
        "check_func": "check_mysql_relay_log_basename",
    }, {
        "check_name": "确保general_log_file具有适当的权限",
        "is_scored": "1",
        "applicability": "基础安全措施",
        "description": """MySQL可以使用各种日志文件进行操作，每个日志文件用于不同的目的。这些是二进制日志，错误日志，慢查询日志，中继日志和常规日志。
    因为这些是文件在主机操作系统上，它们受制于主机，除MySQL用户外，其他用户也可以访问。""",
        "rationale": """限制这些对象的可访问性将保护机密性，完整性和安全性、MySQL日志的可用性。""",
        "audit": """执行以下步骤来评估此建议：
1. 通过执行以下语句找到general_log_file值：show variables like 'general_log_file'; 
2. 检查general_log_file的用户和组的权限为 mysql:mysql 执行权限为 660 
""",
        "remediation": """对每个需要更正权限的日志文件位置执行以下命令： 
chmod 660 <log file>  
chown mysql:mysql <log file> 
""",
        "impact": """更改日志文件的权限可能会影响使用日志文件适配器的监视工具。此外，慢速查询日志还可用于以下方面的性能分析：  
应用程序开发人员。  
如果中继日志和二进制日志文件的权限被意外更改为排除用于运行MySQL服务的用户帐户，则可能会中断复制。  
二进制日志文件可用于时间点恢复，因此这也会影响备份，恢复和灾难恢复程序。""",
        "default_value": None,
        "references": None,
        "check_func": "check_mysql_general_log_file",
    }, {
        "check_name": "确保SSL密钥文件具有适当的权限",
        "is_scored": "1",
        "applicability": "基础安全措施",
        "description": "配置为使用SSL/TLS时，MySQL依赖于密钥文件，这些文件存储在主机的文件系统。这些密钥文件受主机的权限结构约束。",
        "rationale": """限制这些对象的可访问性将保护机密性，完整性和安全性。MySQL数据库的可用性以及与客户端的通信。  
如果攻击者知道SSL密钥文件的内容，则他或她可能会冒充服务器。这可以用于中间人攻击。  
根据SSL密码套件的不同，密钥也可能用于先前的解密  捕获的网络流量。""",
        "audit": """要评估此建议，请通过执行以下SQL查找正在使用的SSL密钥语句以获取ssl_key的值：
show variables where variable_name = 'ssl_key'; 
然后，执行以下命令以评估值的权限：
ls -l <ssl_key Value> | egrep "^-r--------[ \t]*.[ \t]*mysql[ \t]*mysql.*$" 
上面命令的输出不足意味着发现。
    """,
        "remediation": """在终端提示符下执行以下命令，以使用审核程序的价值：
chown mysql:mysql <ssl_key Value>  chmod 400 <ssl_key Value>
""",
        "impact": """如果密钥文件的权限更改不正确，则可能导致SSL被禁用重新启动MySQL或可能导致MySQL根本无法启动时。  
如果其他应用程序使用相同的密钥对，则更改密钥的权限文件将影响此应用程序。如果是这种情况，则必须为MySQL的。      
    """,
        "default_value": None,
        "references": "http://dev.mysql.com/doc/refman/5.7/en/ssl-connections.html",
        "check_func": "check_mysql_ssl_key_files",
    }, {
        "check_name": "确保插件目录具有适当的权限",
        "is_scored": "1",
        "applicability": "基础安全措施",
        "description": "插件目录是MySQL插件的位置。插件是存储引擎或用户定义的函数（UDF）。",
        "rationale": """限制这些对象的可访问性将保护机密性，完整性和安全性，MySQL数据库的可用性。如果有人可以修改插件，那么这些插件服务器启动时可能会加载，并且代码将被执行。""",
        "audit": """要评估此建议，请执行以下SQL语句以发现值的plugin_dir：
show variables where variable_name = 'plugin_dir'; 
然后，在终端提示下执行以下命令（使用发现的  plugin_dir Value ）确定权限。
ls -l <plugin_dir Value>/.. | egrep "^drwxr[-w]xr[-w]x[ \t]*[0-9][ \t]*mysql[  \t]*mysql.*plugin.*$" 
缺乏产出意味着发现。注意：权限旨在为775或755。
""",
        "remediation": """要修复此设置，请在终端提示符下使用以下命令执行以下命令：
chmod 775 <plugin_dir Value> (or use 755)  chown mysql:mysql <plugin_dir Value>    
""",
        "impact": """mysql用户以外的其他用户将不再能够更新和添加/删除插件  除非他们能够切换到mysql用户：  
""",
        "default_value": None,
        "references": "http://dev.mysql.com/doc/refman/5.7/zh-CN/install-plugin.html",
        "check_func": "check_mysql_plugin_directory",
    },
    ]
}

# 总则
General = {
    "name": "总则",
    "v_name": "General",
    "value": [
        {
            "check_name": "确保应用了最新的安全补丁",
            "is_scored": "0",
            "applicability": "基础安全措施",
            "description": "定期发布MySQL服务器更新，以解决错误，缓解漏洞，并提供新功能。建议MySQL安装是最新的最新的安全更新。  ",
            "rationale": """使用MySQL补丁维护货币将有助于降低与已知漏洞相关的风险  MySQL服务器中存在的漏洞。如果没有最新的安全补丁，MySQL可能会已知漏洞，  被攻击者用来获得访问权限。""",
            "audit": """执行以下SQL语句以标识MySQL服务器版本:
SHOW VARIABLES WHERE Variable_name LIKE "version";  
""",
            "remediation": """为您的版本安装最新的修补程序或升级到最新版本。  
""",
            "impact": """要更新MySQL服务器，需要重新启动。
""",
            "default_value": None,
            "references": "http://www.oracle.com/technetwork/topics/security/alerts-086861.html",
            "check_func": "check_mysql_",
        },
        {
            "check_name": "确保TEST数据库未安装",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "默认的MySQL安装附带了一个未使用的数据库TEST，建议删除该测试库。",
            "rationale": """测试数据库可以由所有用户访问，并且消耗系统资源。删除的TES数据库会降低MySQL服务器的受攻击面。""",
            "audit": """执行以下语句：
SHOW DATABASES LIKE 'test';
不应该有返回结果。
""",
            "remediation": """执行以下语句去删除测试数据库
DROP DATABASE "test";       
注意：mysql_secure_installation执行此操作以及其他安全性-相关活动。  
""",
            "impact": None,
            "default_value": None,
            "references": "http://dev.mysql.com/doc/refman/5.7/en/mysql-secure-installation.html",
            "check_func": "check_mysql_test_database",
        },
        {
            "check_name": "确保allow-suspicious-udfs设置为FALSE",
            "is_scored": "1",
            "applicability": "纵深防御措施",
            "description": "此选项可防止将任意共享库函数附加为用户定义的函数  通过检查至少一个名为_init，_deinit ，_reset ，_clear的对应方法，  或_add 。 ",
            "rationale": """禁止加载不包含用户定义函数的共享库，减少服务器的攻击面。""",
            "audit": """执行以下操作以确定推荐状态是否到位： 
* 确保mysqld启动命令总没有 --allow-suspicious-udfs
* 确保mysql配置文件中allow-suspicious-udf参数为 FALSE
""",
            "remediation": """执行以下操作以建立推荐状态：  
* 从 mysqld 的启动命令中删除 --allow-suspicious-udfs 选项 。  
* 从 MySQL 选项文件总删除 allow-suspicious-udfs 参数。  
""",
            "impact": None,
            "default_value": "FALSE",
            "references": None,
            "check_func": "check_mysql_allow_suspicious_udfs",
        },
        {
            "check_name": "确保local_infile设置为FALSE",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "该local_infile参数指示是否位于MySQL客户端的文件可以通过LOAD DATA INFILE或SELECT local_file加载或选择计算机。",
            "rationale": """禁用local_infil e会降低攻击者从受影响的磁盘读取敏感文件的能力服务器通过SQL注入漏洞。""",
            "audit": """执行以下SQL语句，并确保将Value字段设置为OFF ：
SHOW VARIABLES WHERE Variable_name = 'local_infile';  
""",
            "remediation": """将以下行添加到MySQL配置文件的[mysqld ]部分，然后重新启动  MySQL服务：
local-infile=0  
""",
            "impact": """禁用local_infile将影响依赖它的解决方案的功能
""",
            "default_value": None,
            "references": """http://dev.mysql.com/doc/refman/5.7/zh-CN/string-functions.html#function_load-file
        http://dev.mysql.com/doc/refman/5.7/en/load-data.html""",
            "check_func": "check_mysql_local_infile",
        },
        {
            "check_name": "确保mysqld不是以–skip-grant-tables启动",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "该选项使mysqld在不使用特权系统的情况下启动。",
            "rationale": """如果使用此选项，则受影响的服务器的所有客户端都将不受限制地访问所有数据库。""",
            "audit": """执行以下操作以确定推荐状态是否到位:
        1. 打开MySQL配置（例如my.cnf ）文件并搜索skip-grant-tables
        2. 确保skip-grant-table s设置为FALSE
""",
            "remediation": """执行以下操作以建立推荐状态：
打开MySQL配置（例如my.cnf ）文件并设置: skip-grant-tables = FALSE 
""",
            "impact": None,
            "default_value": None,
            "references": "http://dev.mysql.com/doc/refman/5.7/en/server-options.html#option_mysqld_skip-grant-tables",
            "check_func": "check_mysql_skip_grant_tables",
        },
        {
            "check_name": "确保启用–skip-symbolic-links跳过符号链接",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "MySQL的符号链接和跳过符号链接选项确定是否  提供符号链接支持。启用使用符号链接时，它们具有   不同的效果取决于主机平台。当符号链接被禁用时，则   数据库不使用文件中存储的符号链接或表中的条目。",
            "rationale": """防止将符号链接用于数据库文件。这在MySQL时尤其重要  正在以root用户身份执行，因为任意文件都可能会被覆盖。symbolic-links选项可能   允许某人将操作定向到MySQL服务器到其他文件和/或目录。""",
            "audit": """执行以下SQL语句以评估此建议： 
SHOW variables LIKE 'have_symlink'; 
确保VALU返回为 FALSE
""",
            "remediation": """执行以下操作来纠正此设置：
1. 打开MySQL配置文件（my.cnf ）  
2. 找到skip_symbolic_links  
3. 设置skip_symbolic_links 为  'YES' 
注意：如果skip_symbolic_links不存在，将其添加到配置文件中的 mysqld  部分。   
""",
            "impact": None,
            "default_value": None,
            "references": """http://dev.mysql.com/doc/refman/5.7/en/symbolic-links.html
http://dev.mysql.com/doc/refman/5.7/en/server-options.html＃option_mysqld_symbolic-links""",
            "check_func": "check_mysql_skip_symbolic_links",
        },
        {
            "check_name": "确保daemon_memcached插件已禁用",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "InnoDB memcached插件允许用户使用以下命令访问InnoDB中存储的数据：  记忆快取通讯协定。",
            "rationale": """默认情况下，该插件不进行身份验证，这意味着任何有权访问  插件的TCP / IP端口可以访问和修改数据。
        但是，并非所有数据都是默认情况下公开。""",
            "audit": """执行以下SQL语句以评估此建议：
SELECT * FROM information_schema.plugins WHERE PLUGIN_NAME='daemon_memcached';
确保没有返回任何行。
""",
            "remediation": """要修复此设置，请在MySQL命令行客户端中发出以下命令：  
uninstall plugin daemon_memcached; 
这将从MySQL服务器上卸载memcached插件。 
""",
            "impact": None,
            "default_value": None,
            "references": "http://dev.mysql.com/doc/refman/5.7/en/innodb-memcached-security.html",
            "check_func": "check_mysql_daemon_memcached",
        },
        {
            "check_name": "确保secure_file_priv不为空",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "所述secure_file_priv 选项限制到由使用的路径LOAD DATA INFIL 或SELECT  local_file 。建议将此选项设置为包含以下内容的文件系统位置：  仅预期由MySQL加载的资源。 ",
            "rationale": """设置secure_file_priv会降低攻击者从服务器读取敏感文件的能力。  通过SQL注入漏洞影响服务器。 """,
            "audit": """
SHOW GLOBAL VARIABLES WHERE Variable_name = 'secure_file_priv' AND Value<>''; 
注意：值应包含有效路径。
""",
            "remediation": """将以下行添加到MySQL配置文件的[mysqld ]部分，然后重新启动  MySQL服务：
secure_file_priv=<path_to_load_directory>  
注意：值应包含有效路径。 
""",
            "impact": """依赖于从各个子目录加载数据的解决方案可能会带来负面影响受此更改的影响。考虑将加载目录合并到一个公共父目录下目录。
""",
            "default_value": None,
            "references": "http://dev.mysql.com/doc/refman/5.7/en/server-system-variables.html#sysvar_secure_file_priv",
            "check_func": "check_mysql_secure_file_priv",
        },
        {
            "check_name": "确保sql_mode包含STRICT_ALL_TABLES",
            "is_scored": "1",
            "applicability": "纵深防御措施",
            "description": """做出数据更改语句（即INSERT ，UPDATE ）时，MySQL可以处理无效或缺少值的方式有所不同，具体取决于是否启用了严格的SQL模式。
什么时候启用严格的SQL模式，数据可能不会被截断或“调整”以使  数据更改语句的工作。""",
            "rationale": """如果没有严格模式，则服务器可能会尝试在可能出现错误的情况下继续执行操作  是一个更安全的选择。
        例如，默认情况下，MySQL将截断数据  不适合可能会导致未知行为或被攻击者利用的领域  规避数据验证。""",
            "audit": """要审核此建议，请执行以下查询：            
SHOW VARIABLES LIKE 'sql_mode';              
确保STRICT_ALL_TABLES在返回的列表中。""",
            "remediation": """将 STRICT_ALL_TABLES 添加到 sql_mode 参数中，并修改在配置文件中。 
""",
            "impact": """依赖MySQL数据库的应用程序应注意STRICT_ALL_TABLES在  使用，以便正确处理错误条件。 
""",
            "default_value": None,
            "references": "http://dev.mysql.com/doc/refman/5.7/en/sql-mode.html",
            "check_func": "check_mysql_sql_mode",
        },
    ]
}

# MySQL权限
MySQLPermissions = {
    "name": "MySQL权限",
    "v_name": "MySQLPermissions",
    "value": [
        {
            "check_name": "确保只有管理用户具有完整的数据库访问权限",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": """mysql.user 和 mysql.db 表列出了各种授予用户的权限，其中一些需要关注的权限包括：
            Select_priv, Insert_priv, Update_priv, Delete_priv, Drop_priv等。
            通常，这些权限并非对每个MySQL用户都可用，并且通常将保留给管理员使用。
            """,
            "rationale": """限制 MySQL 数据库的可访问性将保护机密性、完整性、以及存储在MySQL中的数据可用性。
            具有直接访问权限的用户，有可能可以查看密码的哈希值，或者修改并破坏数据信息。""",
            "audit": """执行以下SQL语句以评估此建议：
SELECT  
  USER, host  
FROM  
  mysql. USER  
WHERE  
  (
    Select_priv  = 'Y') 
    OR  (
      Insert_priv  = 'Y') 
      OR  (
        Update_priv  = 'Y') 
        OR  (
          Delete_priv  = 'Y') 
          OR  (
            Create_priv  = 'Y') 
            OR  (
              Drop_priv  = 'Y');

SELECT  
  USER, host  
FROM  
  mysql. db  
WHERE  
  db  = 'mysql' 
  AND  ((
    Select_priv  = 'Y') 
    OR  (
      Insert_priv  = 'Y') 
      OR  (
        Update_priv  = 'Y') 
        OR  (
          Delete_priv  = 'Y') 
          OR  (
            Create_priv  = 'Y') 
            OR  (
              Drop_priv  = 'Y')
            );
确保返回的所有用户均为管理用户。
    """,
            "remediation": """
执行以下操作来纠正此设置：  
1.列举审计程序产生的非管理用户   
2.对于每个非管理员用户，请使用REVOKE语句删除特权，
    """,
            "impact": """应考虑每个需要的用户需要哪些特权交互式数据库访问。
    """,
            "default_value": None,
            "references": "",
            "check_func": "check_mysql_full_database_access",
        },
        {
            "check_name": "确保非管理用户的file_priv未设置为Y",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": """mysql.use r表中的File_priv特权用于允许或禁止用户从读取和写入服务器主机上的文件。具有File_priv权限的任何用户授予具有以下能力：
1. 从本地文件系统中读取MySQL服务器可读的文件（此包括全局可读的文件）
2. 将文件写到MySQL服务器具有写访问权的本地文件系统""",
            "rationale": """该File_pri v权限允许MySQL的用户从磁盘，将文件写入读取文件到磁盘。  
            攻击者可能利用它来进一步破坏MySQL。应该注意MySQL服务器不应覆盖现有文件。""",
            "audit": """执行以下SQL语句以审核此设置 
select user, host from mysql.user where File_priv = 'Y';
确保结果集中仅返回管理用户。  
""",
            "remediation": """执行以下步骤来修复此设置：  
            1.列举在审计结果集中发现的非管理用户程序  
            2.对于每个用户，发出以下SQL语句：：REVOKE FILE ON *.* FROM '<user>';
""",
            "impact": None,
            "default_value": None,
            "references": "http://dev.mysql.com/doc/refman/5.7/en/privileges-provided.html#priv_file  ",
            "check_func": "check_mysql_file_priv",
        },
        {
            "check_name": "确保非管理用户的process_priv未设置为Y",
            "is_scored": "1",
            "applicability": "纵深防御措施",
            "description": "在mysql.user表中找到的PROCESS特权确定给定用户是否可以  查看所有会话的语句执行信息。",
            "rationale": """该过程的权限允许校长鉴于当前执行的MySQL语句超出了它们自己的范围，包括用于管理密码的语句。这可以被利用攻击者入侵MySQL或获取对潜在敏感数据的访问权限。 """,
            "audit": """执行以下SQL语句来审核此设置：select user, host from mysql.user where Process_priv = 'Y'; 确保结果集中仅返回管理用户。  
""",
            "remediation": """执行以下步骤来修复此设置：  
            1.列举在审计结果集中发现的非管理用户程序  
            2.对于每个用户，发出以下SQL语句REVOKE PROCESS ON *.* FROM '<user>'; 
""",
            "impact": """拒绝PROCESS特权的用户也可能无法使用SHOW ENGINE 
""",
            "default_value": None,
            "references": "http://dev.mysql.com/doc/refman/5.7/en/privileges-provided.html#priv_process ",
            "check_func": "check_mysql_process_priv",
        },
        {
            "check_name": "确保非管理用户的super_priv未设置为Y",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "mysql.user表中的SUPER特权控制着各种MySQL的使用  特征。这些功能包括CHANGE MASTER TO, KILL, mysqladminkill选项，PURGE  BINARY LOGS, SET GLOBAL, mysqladmindebug选项，记录控制等等。",
            "rationale": """所述SUPER权限允许委托人执行许多动作，包括视图和终止当前正在执行的MySQL语句（包括用于管理的语句） 密码）。此特权还提供了配置MySQL的功能，例如  启用/禁用日志记录，更改数据，禁用/启用功能。限制具有   所述SUPER特权减少了攻击者可以利用这些能力的机会。 """,
            "audit": """执行以下SQL语句来审核此设置：select user, host from mysql.user where Super_priv = 'Y'; 确保结果集中仅返回管理用户。  
""",
            "remediation": """执行以下步骤来修复此设置：  
            1.列举在审计结果集中发现的非管理用户程序  
            2.对于每个用户，发出以下SQL语句REVOKE PROCESS ON *.* FROM '<user>'; 
""",
            "impact": """当给定用户拒绝SUPER特权时，该用户将无法获取某些功能的优势，例如某些mysqladmi n选项。
""",
            "default_value": None,
            "references": "http://dev.mysql.com/doc/refman/5.7/zh-CN/privileges-provided.html#priv_super",
            "check_func": "check_mysql_super_priv",
        },
        {
            "check_name": "确保非管理用户的shutdown_priv未设置为Y",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "mysqladmin命令，该命令允许具有SHUTDOWN特权的用户关闭MySQL服务器。 ",
            "rationale": """该SHUTDOWN权限允许校长关机的MySQL。这可能会被攻击者会对MySQL的可用性产生负面影响。 """,
            "audit": """执行以下SQL语句来审核此设置：
             SELECT user, host FROM mysql.user WHERE Shutdown_priv = 'Y'; 确保结果集中仅返回管理用户。  
""",
            "remediation": """执行以下步骤来修复此设置：  
            1.列举在审计结果集中发现的非管理用户程序  
            2.对于每个用户，发出以下SQL语句REVOKE SHUTDOWN ON *.* FROM '<user>'; 
""",
            "impact": None,
            "default_value": None,
            "references": "http://dev.mysql.com/doc/refman/5.7/en/privileges-  provided.html#priv_shutdown",
            "check_func": "check_mysql_shutdown_priv",
        },
        {
            "check_name": "确保非管理用户的create_user_priv未设置为Y",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "CREATE USER特权控制着给定用户添加或删除用户的权利，更改现有用户的名称，或撤销现有用户的权限。",
            "rationale": """减少授予CREATE USE R权限的用户数量，可以最大程度地减少能够添加/删除用户，更改现有用户的名称以及操纵现有用户的用户的用户特权。 """,
            "audit": """执行以下SQL语句来审核此设置：
                         SELECT user, host FROM mysql.user WHERE Create_user_priv = 'Y';  确保结果集中仅返回管理用户。  
            """,
            "remediation": """执行以下步骤来修复此设置：  
                        1.列举在审计结果集中发现的非管理用户程序  
                        2.对于每个用户，发出以下SQL语句REVOKE CREATE ON *.* FROM '<user>'; 
            """,
            "impact": None,
            "default_value": None,
            "references": "",
            "check_func": "check_mysql_create_user_priv",
        },
        {
            "check_name": "确保非管理用户的grant_priv未设置为Y",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "在GRANT OPTION特权存在于不同的上下文（mysql.user ，mysql.db ）为  控制特权用户操纵其他特权的能力的目的  用户。",
            "rationale": """在GRANT特权允许委托人授予其他主体的额外特权。这个  可能被攻击者用来破坏MySQL。 """,
            "audit": """执行以下SQL语句来审核此设置：
            SELECT user, host FROM mysql.user WHERE Grant_priv = 'Y';  
            SELECT user, host FROM mysql.db WHERE Grant_priv = 'Y'; 
            确保结果集中仅返回管理用户。
""",
            "remediation": """执行以下步骤来修复此设置：  
                        1.列举在审计结果集中发现的非管理用户程序  
                        2.对于每个用户，发出以下SQL语句REVOKE GRANT OPTION ON *.* FROM '<user>'; 
            """,
            "impact": None,
            "default_value": None,
            "references": "http://dev.mysql.com/doc/refman/5.7/en/privileges-provided.html#priv_grant-  option ",
            "check_func": "check_mysql_grant_priv",
        },
        {
            "check_name": "确保非Slave用户的repl_slave_priv未设置为Y",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "replication slave 权限允许从库请求主服务器上进行的更新记录",
            "rationale": """该REPLICATION SLAVE权限允许委托人获得一个包含所有数据的二进制日志文件  主服务器更改语句和/或更改表数据。这可以由  攻击者从MySQL中读取/获取敏感数据。 """,
            "audit": """执行以下SQL语句来审核此设置：   
            SELECT user, host FROM mysql.user WHERE Repl_slave_priv = 'Y';确保仅为从属用户指定的帐户被授予此特权。
""",
            "remediation": """执行以下步骤来修复此设置：  
            1.列举在审核程序结果集中找到的非从属用户 
            2.对于每个用户，发出以下SQL语句REVOKE REPLICATION SLAVE ON *.* FROM '<user>'; 
""",
            "impact": None,
            "default_value": None,
            "references": "http://dev.mysql.com/doc/refman/5.7/en/privileges-provided.html#priv_replication-slave",
            "check_func": "check_mysql_repl_slave_priv",
        },
        {
            "check_name": "确保DML/DDL授权仅限于特定数据库和用户",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "DML/DDL包括用于修改或创建数据结构的特权集。这个包括INSERT ，SELECT ，UPDATE ，DELETE ，DROP ，CREATE和ALTER特权",
            "rationale": """INSERT ，SELECT ，UPDATE ，DELETE ，DROP ，CREATE和ALTE R在任何情况下都是强大的特权  数据库。此类特权应仅限于那些需要此类权限的用户。通过使用这些权利限制用户并确保他们仅限于特定的数据库，  减少了数据库的攻击面。""",
            "audit": """执行以下SQL语句来审核此设置： 
            SELECT User,Host,Db  FROM mysql.db  WHERE Select_priv='Y'  OR Insert_priv='Y'  
            OR Update_priv='Y'  OR Delete_priv='Y'  OR Create_priv='Y'  OR Drop_priv='Y'  OR Alter_priv='Y'; 
确保所有返回的用户应在指定的数据库上具有这些特权。 
""",
            "remediation": """  
            REVOKE SELECT ON <host>.<database> FROM <user>;  
            REVOKE INSERT ON <host>.<database> FROM <user>;  
            REVOKE UPDATE ON <host>.<database> FROM <user>;  
            REVOKE DELETE ON <host>.<database> FROM <user>;  
            REVOKE CREATE ON <host>.<database> FROM <user>;  
            REVOKE DROP ON <host>.<database> FROM <user>; 
            REVOKE ALTER ON <host>.<database> FROM <user>;
""",
            "impact": None,
            "default_value": None,
            "references": None,
            "check_func": "check_mysql_ddl_dml_privileges",
        },
    ]
}

# 审核和记录
AuditingAndLogging = {
    "name": "审核和记录",
    "v_name": "AuditingAndLogging",
    "value": [
        {
            "check_name": "确保 log_error 记录不为空",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "错误日志包含有关事件的信息，例如mysqld的启动和停止，何时需要检查或修复表，以及取决于主机 系统，mysqld失败时的堆栈跟踪。 ",
            "rationale": """启用错误记录功能可以提高检测针对MySQL的恶意尝试的能力，和其他重要消息，例如如果未启用错误日志，则表明连接错误  可能会被忽略。""",
            "audit": """执行以下SQL语句来审核此设置：
            SHOW variables LIKE 'log_error';
            确保不返回空值
""",
            "remediation": """执行以下操作来纠正此设置：
            1. 打开配置文件 my.cnf
            2. 设置 log-error 参数指定错误日志的路径
""",
            "impact": None,
            "default_value": None,
            "references": "http://dev.mysql.com/doc/refman/5.7/en/error-log.html  ",
            "check_func": "check_mysql_log_error",
        },
        {
            "check_name": "确保日志文件存储在非系统分区上",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "可以在MySQL配置中将MySQL日志文件设置为存在于文件系统。这是常见的做法，以确保系统文件系统被留下整洁应用程序日志。系统文件系统包括root，/ var或/ usr 。 ",
            "rationale": """将MySQL注销移出系统分区将减少拒绝的可能性通过将可用磁盘空间用尽给操作系统来提供服务。""",
            "audit": """执行以下SQL语句以评估此建议： 
            SELECT @@global.log_bin_basename;
            确保返回的值不是 /, /var, /user
""",
            "remediation": """执行以下操作来纠正此设置：
            1. 打开配置文件 my.cnf
            2. 设置 log-bin 参数指定系统分区的文件系统路径
""",
            "impact": None,
            "default_value": None,
            "references": """http://dev.mysql.com/doc/refman/5.7/en/binary-log.html
  http://dev.mysql.com/doc/refman/5.7/en/replication-options-binary-log.html""",
            "check_func": "check_mysql_log_error",
        },
        {
            "check_name": "确保 log_error_verbosity 未设置为 1",
            "is_scored": "1",
            "applicability": "纵深防御措施",
            "description": """
            log_error_verbosity系统变量向MySQL提供其他日志信息：
            1：启用错误消息。
            2：启用错误和警告消息，
            3：记录错误、警告和提示等消息。
            """,
            "rationale": """这可能有助于通过记录通信错误和中止检测恶意行为连接。""",
            "audit": """执行以下SQL语句以评估此建议： 
            SHOW GLOBAL VARIABLES LIKE 'log_error_verbosity';  
            确保返回的值不是1
""",
            "remediation": """执行以下操作来纠正此设置：
            1. 打开配置文件 my.cnf
            2. 设置 log_error_verbosity = 2 或者 3
""",
            "impact": None,
            "default_value": None,
            "references": """https://dev.mysql.com/doc/refman/5.7/en/server-system-variables.html#sysvar_log_error_verbosity""",
            "check_func": "check_mysql_log_error_verbosity",
        },
        {
            "check_name": "确保审核日志记录已启用",
            "is_scored": "0",
            "applicability": "纵深防御措施",
            "description": """
            审计日志未真正包含在MySQL的社区版中-仅常规日志。可以使用常规日志，但不切实际，因为它会快速增长并具有对服务器性能的不利影响。  
            但是，启用审核日志记录是生产中的重要考虑因素环境，并且确实存在第三方工具可以提供帮助。为启用审核日志记录:
            1. 互动用户会话  
            2. 申请会议（可选)
            """,
            "rationale": """审核日志记录有助于确定谁更改了内容和时间。审核日志可能用作调查证据。这也有助于确定攻击者做了什么。""",
            "audit": """验证是否安装了第三方工具并将其配置为启用交互式日志记录  用户会话和（可选）应用程序会话。
""",
            "remediation": """从各种来源获得第三方MySQL日志记录解决方案 ，包括但不限于以下内容：
            1. 通用查询日志  
            2. MySQL企业审核  
            3. 适用于MySQL的MariaDB审核插件  
            4. McAfee MySQL审核
""",
            "impact": None,
            "default_value": None,
            "references": """1. http://dev.mysql.com/doc/refman/5.7/en/query-log.html  
            2. http://dev.mysql.com/doc/refman/5.7/en/mysql-enterprise-audit.html  
            3. https://mariadb.com/kb/en/server_audit-mariadb-audit-plugin/  
            4. https://github.com/mcafee/mysql-audit""",
            "check_func": "check_mysql_log_error_verbosity",
        },
        {
            "check_name": "确保 log-raw设置为 OFF",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": """
            log-raw MySQL选项确定服务器是否重写密码，因此  以免在日志文件中以纯文本形式出现。
            如果启用了log-raw，则将写入密码以纯文本格式显示到各种日志文件（常规查询日志，慢速查询日志和二进制日志）。
            """,
            "rationale": """启用了密码的原始日志记录后，可以访问日志文件的人可能会看到普通信息文字密码。""",
            "audit": """执行以下操作来评估此建议：
            查看my.cnf配置文件中的参数 确保 log-raw = OFF 
""",
            "remediation": """修改配置文件设置 log-raw = OFF 
""",
            "impact": None,
            "default_value": "OFF",
            "references": """http://dev.mysql.com/doc/refman/5.7/en/password-logging.html  
            http://dev.mysql.com/doc/refman/5.7/en/server-options.html#option_mysqld_log-raw""",
            "check_func": "check_mysql_log_raw",
        },
    ]
}

# 身份验证
Authentication = {
    "name": "身份验证",
    "v_name": "Authentication",
    "value": [
        {
            "check_name": "确保密码不存储在全局配置中",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "MySQL 配置文件 [client] 部分允许将 user password 配置在文件中。验证是否在全局配置中使用了明文的password",
            "rationale": """使用password参数可能会对用户的密码机密性产生负面影响。""",
            "audit": """要评估此建议，请执行以下步骤：
            1. 打开MySQL配置文件（例如my.cnf）  
            2. 检查MySQL配置文件的[client]部分，并确保密码没有配置""",
            "remediation": """使用mysql_config_editor将身份验证凭据以加密形式存储在中.mylogin.cnf。  
        """,
            "impact": """默认情况下，系统上的所有用户均可读取全局配置。这是必需的全局默认值（提示，端口，套接字等）。如果此文件中存在密码，则全部  系统上的用户可能可以访问它。
        """,
            "default_value": None,
            "references": "1. http://dev.mysql.com/doc/refman/5.7/en/mysql-config-editor.html ",
            "check_func": "check_mysql_password_not_in_cnf",
        },
        {
            "check_name": "确保 sql_mode 包含 NO_AUTO_CREATE_USER",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "NO_AUTO_CREATE_USE R是sql_mode的选项，可防止GRANT语句不提供身份验证信息时自动创建用户。",
            "rationale": """空白密码会抵消身份验证机制提供的好处。没有这个设置管理用户可能会意外地创建一个没有密码的用户。""",
            "audit": """执行以下SQL语句以评估此建议：
            SELECT @@global.sql_mode;  
            SELECT @@session.sql_mode;
            确保每个结果都包含NO_AUTO_CREATE_USER 
        """,
            "remediation": """执行以下操作来纠正此设置： 
            1.打开MySQL配置文件（my.cnf ） 
            2.查找的sql_mode在设定的[mysqld]区   
            3.将NO_AUTO_CREATE_USER添加到sql_mode设置 
        """,
            "impact": None,
            "default_value": None,
            "references": "",
            "check_func": "check_mysql_not_auto_create_user",
        },
        {
            "check_name": "确保为所有MySQL帐户设置密码",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "空白密码允许用户不使用密码即可登录。",
            "rationale": """没有密码，仅知道用户名和允许的主机列表即可  有人可以连接到服务器并采用用户身份。实际上,绕过身份验证机制。""",
            "audit": """执行以下SQL查询以确定是否有用户具有空密码：
            SELECT User,host  FROM mysql.user  WHERE authentication_string=''; 
            如果所有帐户都设置了密码，则不会返回任何行。
        """,
            "remediation": """对于审核程序返回的每一行，使用以下命令为给定用户设置密码：  以下语句（作为示例）：
            SET PASSWORD FOR <user>@'<host>' = '<clear password>'
            注意：用适当的值替换<user> ，<host>和<clear password > 
        """,
            "impact": None,
            "default_value": None,
            "references": "https://dev.mysql.com/doc/refman/5.7/en/assigning-passwords.html",
            "check_func": "check_mysql_user_password",
        },
        {
            "check_name": "确保 default_password_lifetime 小于或等于 90",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "",
            "rationale": """""",
            "audit": """
            SHOW VARIABLES LIKE 'default_password_lifetime'; 
            default_password_lifetime 小于或等于90
        """,
            "remediation": """SET GLOBAL default_password_lifetime=90;
            ALTER USER 'jeffrey'@'localhost' PASSWORD EXPIRE INTERVAL 90 DAY;
        """,
            "impact": """在受控环境中依赖自动登录的脚本客户端或用户将需要考虑他们的身份验证程序。服务器将接受用户，但用户处于受限模式。
        """,
            "default_value": "360",
            "references": "1. https://dev.mysql.com/doc/refman/5.7/en/password-expiration-policy.html  2. https://dev.mysql.com/doc/refman/5.7/en/password-expiration-sandbox-  mode.html  ",
            "check_func": "check_mysql_default_password_lifetime",
        },
        {
            "check_name": "确保密码复杂性到位",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "密码复杂度包括密码特征，例如长度，大小写，长度和  字符集。",
            "rationale": """复杂的密码有助于缓解字典，暴力破解和其他密码攻击。此建议可防止用户选择较弱的密码,容易被猜到。""",
            "audit": """执行以下SQL语句以评估此建议：
            SHOW VARIABLES LIKE 'validate_password%'; 
            * validate_password_length >= 14
            * validate_password_mixed_case_countshould >= 1  
            * validate_password_number_countshould >= 1
            * validate_password_special_char_count >= 1
            * validate_password_policy MEDIUM 或 STRONG
            全局配置中应包含以下几行：
            plugin-load=validate_password.so  
            validate-password=FORCE_PLUS_PERMANENT
            检查用户的密码是否与用户名相同：
            SELECT user,authentication_string,host FROM mysql.user  
            WHERE authentication_string=CONCAT('*', UPPER(SHA1(UNHEX(SHA1(user)))));
            注意：此方法只能检查4.1后的密码格式，该格式也可以称为mysql_native_password
        """,
            "remediation": """添加到全局配置：
            plugin-load=validate_password.so  
            validate-password=FORCE_PLUS_PERMANENT  
            validate_password_length=14  
            validate_password_mixed_case_count=1  
            validate_password_number_count=1  
            validate_password_special_char_count=1  
            validate_password_policy=MEDIUM 
            并为密码与用户相同的用户更改密码用户名。
        """,
            "impact": """对此建议的补救措施需要重新启动服务器
        """,
            "default_value": None,
            "references": "http://dev.mysql.com/doc/refman/5.7/en/validate-password-plugin.html",
            "check_func": "check_mysql_validate_password",
        },
        {
            "check_name": "确保没有用户具有通配符主机名",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": """向特定用户授予权限时，MySQL可以使用主机通配符数据库。对于例如，可以授予一给定特权 '<user>'@'%'
            """,
            "rationale": """避免在主机名中使用通配符有助于从以下位置控制特定位置给定用户可以连接到数据库并与之交互的数据库。""",
            "audit": """执行以下SQL语句以评估此建议:
            SELECT user, host FROM mysql.user WHERE host = '%';  
            确保不返回任何行。
        """,
            "remediation": """执行以下操作来纠正此设置：
            1.枚举运行审核过程后返回的所有用户   
            2.更改用户的主机名或删除用户的主机
        """,
            "impact": None,
            "default_value": None,
            "references": None,
            "check_func": "check_mysql_hildcard_wostnames",
        },
        {
            "check_name": "确保不存在匿名帐户",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "匿名帐户是具有空用户名（''）的用户。匿名帐号没有密码，因此任何人都可以使用它们连接到MySQL服务器。",
            "rationale": """删除匿名帐户将有助于确保仅确定和信任的主体  能够与MySQL进行交互。""",
            "audit": """执行以下SQL查询以标识匿名帐户：
            SELECT user,host FROM mysql.user WHERE user = '';   
            如果没有匿名帐户，则上面的查询将返回零行。
        """,
            "remediation": """执行以下操作来纠正此设置：  
            1.枚举执行审计过程返回的匿名用户   
            2.对于每个匿名用户，
            请DROP或为其分配一个名称。
            作为替代方案，您可以执行mysql_secure_installatio效用。
        """,
            "impact": """任何依赖匿名数据库访问的应用程序都会受到此不利影响更改。
        """,
            "default_value": "使用标准安装脚本mysql_install_db，它将创建两个匿名  帐户：一个用于主机localhost，另一个用于网络接口的IP地址。 ",
            "references": """1. http://dev.mysql.com/doc/refman/5.7/en/mysql-secure-installation.html  2. https://dev.mysql.com/doc/refman/5.6/en/default-privileges.html  """,
            "check_func": "check_mysql_anonymous_accounts",
        },
    ]
}

# 网络
Network = {
    "name": "网络",
    "v_name": "Network",
    "value": [
        {
            "check_name": "确保将 have_ssl 设置为 YES",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "在不受信任的网络上传输时，所有网络流量都必须使用SSL/TLS",
            "rationale": """受SSL/TLS保护的MySQL协议有助于防止窃听和人工干预中间攻击。""",
            "audit": """SHOW variables WHERE variable_name = 'have_ssl';  
            确保变量的值为 Yes。注意：从MySQL 5.0.38开始，have_openssl是have_ssl的别名。可以构建MySQL与OpenSSL或YaSSL。 
""",
            "remediation": """请按照《 MySQL 5.6参考手册》中记录的步骤设置SSL。  
""",
            "impact": """启用S​​SL将使客户端可以加密网络流量并验证身份。  服务器。这可能会影响网络流量检查。
""",
            "default_value": "DISABLED",
            "references": """1. http://dev.mysql.com/doc/refman/5.7/en/ssl-connections.html 
            2. http://dev.mysql.com/doc/refman/5.7/en/ssl-options.htm""",
            "check_func": "check_mysql_have_ssl",
        },
        {
            "check_name": "确保将 ssl_type 设置为ANY、X509、SPECIFIED",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "在不受信任的网络上传输时，所有网络流量都必须使用SSL/TLS，对于通过以下方式进入系统的用户，应按用户强制实施SSL / TLS：  网络。",
            "rationale": """受SSL/TLS保护的MySQL协议有助于防止窃听和人工干预中间攻击。""",
            "audit": """SELECT user, host, ssl_type FROM mysql.user  
            WHERE NOT HOST IN ('::1', '127.0.0.1', 'localhost');
            ssl_type 应该是 ANY, X509, or SPECIFIED.  
            从MySQL 5.0.38开始，have_openssl是have_ssl的别名。可以构建MySQL与OpenSSL或YaSSL。 
""",
            "remediation": """使用GRANT语句要求使用SSL：
            GRANT USAGE ON *.* TO 'my_user'@'app1.example.com' REQUIRE SSL; 
            请注意，REQUIRE SSL仅强制实施SSL。有诸如REQUIRE X509，REQUIRE之类的选项  ISSUER，REQUIRE SUBJECT，可用于进一步限制连接选项。 
""",
            "impact": """强制实施SSL / TLS时，不使用SSL的客户端将无法连接。如果  未为服务器配置SSL / TLS，则必须配置SSL / TLS的帐户  将无法连接 
""",
            "default_value": "NULL",
            "references": """1. http://dev.mysql.com/doc/refman/5.7/en/ssl-connections.html  
            2. http://dev.mysql.com/doc/refman/5.7/en/grant.html  """,
            "check_func": "check_mysql_have_ssl",
        },

    ]
}

# 复制
Replication = {
    "name": "复制",
    "v_name": "Replication",
    "fields": [],
    "value": [
        {
            "check_name": "确保复制流量安全",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "服务器之间的复制流量应得到保护。",
            "rationale": """复制流量应得到保护，因为它可以访问所有传输的信息  并可能泄露密码。""",
            "audit": """检查复制流量是否正在使用
* 私人网路  
* 虚拟专用网  
* SSL / TLS  
* SSH隧道 
""",
            "remediation": """保护网络流量 
""",
            "impact": """如果复制流量不受保护，则有人可能会捕获密码和其他敏感信息发送到从站时。 
""",
            "default_value": None,
            "references": None,
            "check_func": "check_mysql_replication_traffic",
        },
        {
            "check_name": "确保 MASTER_SSL_VERIFY_SERVER_CERT 设置为 YES 或 1",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "在MySQL从属上下文中，设置MASTER_SSL_VERIFY_SERVER_CER T指示是否  从机应验证主机的证书。此配置项可以设置为叶小号或   否，除非已在从属服务器上启用SSL，否则将忽略该值。",
            "rationale": """使用SSL时，证书验证对于验证与之相关的一方非常重要。  
            正在建立连接。在这种情况下，从服务器（客户端）应验证主服务器的   （服务器的）证书以在继续连接之前对主服务器进行身份验证。
            """,
            "audit": """要评估此建议，请发出以下声明：
            select ssl_verify_server_cert from mysql.slave_master_info; 
            验证ssl_verify_server_cer t的值为1
""",
            "remediation": """要修复此设置，必须使用CHANGE MASTER TO命令
            STOP SLAVE; -- required if replication was already running  
            CHANGE MASTER TO MASTER_SSL_VERIFY_SERVER_CERT=1;  
            START SLAVE; -- required if you want to restart replication   
""",
            "impact": """使用CHANGE MASTER TO时，请注意以下几点：  
1. 在执行CHANGE MASTER TO  之前，需要停止从属进程。
2. 使用CHANGE MASTER TO会启动新的中继日志，而不会保留旧的日志，除非明确告知要保留它们 
3. 当CHANGE MASTER TO被调用时，一些信息转储到错误日志 （对于以前的值MASTER_HOST，MASTER_PORT，MASTER_LOG_FILE ，和  MASTER_LOG_POS ）  
4. 调用CHANGE MASTER T O将隐式提交任何正在进行的事务  
""",
            "default_value": None,
            "references": "https://dev.mysql.com/doc/refman/5.6/en/change-master-to.html",
            "check_func": "check_mysql_master_ssl_verify",
        },
        {
            "check_name": "确保 master_info_repository 设置为 TABLE",
            "is_scored": "1",
            "applicability": "纵深防御措施",
            "description": "所述master_info_repository设置确定到从属记录主控状态和连接信息。选项为FILE或TABLE 。另请注意，此设置是   也与sync_master_info设置相关联。",
            "rationale": """客户端使用的密码存储在主信息存储库中，通过 默认为纯文本文件。TABLE主信息存储库更安全一些，但具有文件系统访问，仍然可以访问从站正在使用的密码。 """,
            "audit": """执行以下SQL语句以评估此建议: 
            SHOW GLOBAL VARIABLES LIKE 'master_info_repository';  
            结果应为TABLE而不是FILE。
""",
            "remediation": """执行以下操作来纠正此设置：
            1.打开MySQL配置文件（my.cnf ）  
            2.找到master_info_repository  
            3.设置的master_info_repository值表  
            注意：如果master_info_repository不存在，请将其添加到配置文件中。 
""",
            "impact": None,
            "default_value": None,
            "references": "http://dev.mysql.com/doc/refman/5.7/en/replication-options-slave.html＃sysvar_master_info_repository",
            "check_func": "check_mysql_master_info_repository",
        },
        {
            "check_name": "确保复制用户的 super_priv 未设置为 Y",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": "mysql.user表中的SUPER特权控制着各种MySQL的使用  特征。这些功能包括CHANGE MASTER TO, KILL, mysqladminkill选项，PURGE  BINARY LOGS, SET GLOBAL, mysqladmindebug选项，记录控制等等。",
            "rationale": """所述SUPER权限允许委托人执行许多动作，包括视图和终止当前正在执行的MySQL语句（包括用于管理的语句） 密码）。此特权还提供了配置MySQL的功能，例如  启用/禁用日志记录，更改数据，禁用/启用功能。限制具有   所述SUPER特权减少了攻击者可以利用这些能力的机会。 """,
            "audit": """执行以下SQL语句来审核此设置：
            select user, host from mysql.user where user='repl' and Super_priv = 'Y'; 
            确保结果集中仅返回管理用户。  
""",
            "remediation": """执行以下步骤来修复此设置：  
            1.列举在审计结果集中发现的复制用户
            2.对于每个复制用户  ，发出以下SQL语句REVOKE PROCESS ON *.* FROM '<user>'; 
""",
            "impact": """当给定用户拒绝SUPER特权时，该用户将无法获取某些功能的优势，例如某些mysqladmi n选项。
""",
            "default_value": None,
            "references": "http://dev.mysql.com/doc/refman/5.7/zh-CN/privileges-provided.html#priv_super",
            "check_func": "check_mysql_replication_user_super_priv",
        },
        {
            "check_name": "确保没有复制用户具有通配符主机名",
            "is_scored": "1",
            "applicability": "基础安全措施",
            "description": """向特定用户授予权限时，MySQL可以使用主机通配符数据库。对于例如，可以授予一给定特权 '<user>'@'%'
            """,
            "rationale": """避免在主机名中使用通配符有助于从以下位置控制特定位置给定用户可以连接到数据库并与之交互的数据库。""",
            "audit": """执行以下SQL语句以评估此建议:
            SELECT user, host FROM mysql.user WHERE user='repl' AND host = '%';确保不返回任何行。
        """,
            "remediation": """执行以下操作来纠正此设置：
            1.枚举运行审核过程后返回的所有用户   
            2.更改用户的主机名或删除用户的主机
        """,
            "impact": None,
            "default_value": None,
            "references": None,
            "check_func": "check_mysql_replication_user_wildcard_hostnames",
        }

    ]
}

cis_mysql_57_benchmark = [
    OperatingSystemLevelConfiguration,
    InstallationandPlanning,
    FileSystemPermissions,
    General,
    MySQLPermissions,
    AuditingAndLogging, Authentication, Network, Replication
]

params_excel = {"dir_name": "report","report_name": "test"}
excel_api = Outputexcel(**params_excel)
for types in cis_mysql_57_benchmark:
    # print(json.dumps(types, indent=2))
    check_result = list(map(lambda x: x.values(), types["value"]))
    fields = ['基线名', '是否计分1 积分 0 不计分',  '安全等级', '描述', '理论基础', '检查算法', '修复方法', '影响', '默认值', '链接', '检查函数名']
    list_keys = ['check_name', 'is_scored', 'applicability', 'description', 'rationale', 'audit', 'remediation', 'impact', 'default_value', 'references', 'check_func']
    # 3.渲染报告
    excel_api.add_sheet(types["name"], fields, list_keys, check_result)
excel_api.write_close()
