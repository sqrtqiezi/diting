# Rocky Linux 9.6 ECS 部署设置指南

## 概述

本文档补充说明在 Rocky Linux 9.6 环境下部署 Diting 应用的特定配置步骤。Rocky Linux 是 RHEL 兼容的企业级 Linux 发行版,相比 Ubuntu/Debian 系统有一些关键差异。

## 操作系统信息

- **发行版**: Rocky Linux 9.6
- **架构**: x86_64
- **包管理器**: DNF (Dandified YUM)
- **防火墙**: firewalld
- **SELinux**: 默认启用(Enforcing)

## 与 Ubuntu 的主要差异

| 特性 | Rocky Linux 9.6 | Ubuntu 22.04 |
|------|----------------|--------------|
| 包管理器 | `dnf` | `apt` |
| Python 包名 | `python3.12` | `python3.12` |
| Python 开发包 | `python3.12-devel` | `python3.12-dev` |
| 防火墙 | `firewalld` | `ufw` |
| SELinux | 启用 | 未安装 |
| 服务管理 | `systemctl` | `systemctl` (相同) |

## 初始系统配置

### 1. 更新系统

```bash
sudo dnf update -y
sudo dnf install -y epel-release  # 启用 EPEL 仓库
```

### 2. 安装基础工具

```bash
# 开发工具
sudo dnf groupinstall -y "Development Tools"

# 必需的系统工具
sudo dnf install -y \
    git \
    curl \
    wget \
    rsync \
    jq \
    tar \
    gzip
```

## Python 3.12 安装

### 方法 1: 从 EPEL 安装(推荐)

```bash
# 安装 Python 3.12
sudo dnf install -y python3.12 python3.12-devel python3.12-pip

# 验证安装
python3.12 --version  # Python 3.12.x
```

### 方法 2: 从源码编译

```bash
# 安装编译依赖
sudo dnf install -y \
    gcc \
    make \
    openssl-devel \
    bzip2-devel \
    libffi-devel \
    zlib-devel \
    readline-devel \
    sqlite-devel

# 下载并编译 Python 3.12
cd /tmp
wget https://www.python.org/ftp/python/3.12.6/Python-3.12.6.tgz
tar xzf Python-3.12.6.tgz
cd Python-3.12.6

./configure --enable-optimizations --prefix=/usr/local
make -j$(nproc)
sudo make altinstall

# 验证
python3.12 --version
```

## uv 安装

```bash
# 为 deploy 用户安装 uv
sudo su - deploy
curl -LsSf https://astral.sh/uv/install.sh | sh

# 添加到 PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 验证
uv --version
```

## 防火墙配置

Rocky Linux 使用 `firewalld` 而非 `ufw`:

```bash
# 检查防火墙状态
sudo firewall-cmd --state

# 允许 SSH
sudo firewall-cmd --permanent --add-service=ssh

# 允许 HTTP/HTTPS
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https

# 允许应用端口 8000 (如果需要外部访问)
sudo firewall-cmd --permanent --add-port=8000/tcp

# 重载防火墙规则
sudo firewall-cmd --reload

# 查看已配置的规则
sudo firewall-cmd --list-all
```

## SELinux 配置

Rocky Linux 默认启用 SELinux,可能会阻止某些操作。

### 检查 SELinux 状态

```bash
# 查看 SELinux 状态
getenforce  # 输出: Enforcing / Permissive / Disabled

# 查看 SELinux 详细状态
sestatus
```

### 为应用配置 SELinux

#### 选项 1: 允许 Diting 服务网络访问

```bash
# 允许 systemd 服务绑定端口 8000
sudo semanage port -a -t http_port_t -p tcp 8000

# 如果 semanage 未安装
sudo dnf install -y policycoreutils-python-utils
```

#### 选项 2: 为 Diting 目录设置正确的 SELinux 上下文

```bash
# 设置 /opt/diting 目录的 SELinux 上下文
sudo semanage fcontext -a -t httpd_sys_content_t "/opt/diting(/.*)?"
sudo restorecon -Rv /opt/diting

# 允许 systemd 服务读写日志
sudo setsebool -P httpd_can_network_connect 1
```

#### 选项 3: 临时禁用 SELinux(仅用于测试)

```bash
# 临时禁用(重启后恢复)
sudo setenforce 0

# 永久禁用(不推荐用于生产)
sudo vi /etc/selinux/config
# 修改: SELINUX=disabled
# 然后重启
```

**推荐**: 使用选项 1 或 2,保持 SELinux 启用以提高安全性。

## 创建部署用户

```bash
# 创建 deploy 用户
sudo useradd -m -s /bin/bash deploy

# 配置 SSH 目录
sudo mkdir -p /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo chown deploy:deploy /home/deploy/.ssh

# 添加公钥(从本地复制)
# 本地执行: cat ~/.ssh/diting-deploy.pub
# 在 ECS 上:
sudo vi /home/deploy/.ssh/authorized_keys
# 粘贴公钥内容

sudo chmod 600 /home/deploy/.ssh/authorized_keys
sudo chown deploy:deploy /home/deploy/.ssh/authorized_keys

# 测试 SSH 连接(从本地)
ssh deploy@$ECS_IP "echo 'SSH connection successful'"
```

## 配置 sudo 权限

```bash
# 创建 sudoers 文件
sudo vi /etc/sudoers.d/deploy

# 添加以下内容:
deploy ALL=(ALL) NOPASSWD: /bin/systemctl restart diting
deploy ALL=(ALL) NOPASSWD: /bin/systemctl status diting
deploy ALL=(ALL) NOPASSWD: /bin/systemctl daemon-reload
deploy ALL=(ALL) NOPASSWD: /bin/systemctl enable diting
deploy ALL=(ALL) NOPASSWD: /bin/systemctl start diting
deploy ALL=(ALL) NOPASSWD: /bin/systemctl stop diting

# 设置正确的权限
sudo chmod 440 /etc/sudoers.d/deploy

# 验证 sudo 配置
sudo -l -U deploy
```

## 创建部署目录

```bash
# 创建部署目录结构
sudo mkdir -p /opt/diting/releases
sudo chown -R deploy:deploy /opt/diting

# 创建日志目录
sudo mkdir -p /opt/diting/logs
sudo chown deploy:deploy /opt/diting/logs

# 如果 SELinux 启用,设置正确的上下文
sudo semanage fcontext -a -t httpd_sys_rw_content_t "/opt/diting/logs(/.*)?"
sudo restorecon -Rv /opt/diting/logs
```

## 安装 Systemd 服务

```bash
# 从项目复制 systemd 服务文件
sudo cp /path/to/deploy/diting.service /etc/systemd/system/

# 如果 SELinux 启用,恢复正确的上下文
sudo restorecon -v /etc/systemd/system/diting.service

# 重载 systemd
sudo systemctl daemon-reload

# 启用服务(开机自启)
sudo systemctl enable diting

# 不要立即启动,等待首次部署
```

## 配置 journald 日志

```bash
# 编辑 journald 配置
sudo vi /etc/systemd/journald.conf

# 添加或修改以下配置:
[Journal]
SystemMaxUse=500M
SystemKeepFree=1G
MaxRetentionSec=3month

# 重启 journald
sudo systemctl restart systemd-journald
```

## 验证环境

运行以下检查清单确保环境配置正确:

```bash
# 1. Python 版本
python3.12 --version
# 预期: Python 3.12.x

# 2. uv 可用(以 deploy 用户)
su - deploy -c "uv --version"
# 预期: uv x.x.x

# 3. 防火墙规则
sudo firewall-cmd --list-all
# 预期: 包含 ssh, http, https 和可选的 8000/tcp

# 4. SELinux 状态
getenforce
# 预期: Enforcing (推荐)

# 5. Deploy 用户 sudo 权限
sudo -l -U deploy | grep systemctl
# 预期: 包含 restart, status, daemon-reload 权限

# 6. 部署目录
ls -ld /opt/diting
# 预期: drwxr-xr-x. deploy deploy

# 7. SSH 连接(从本地测试)
ssh deploy@$ECS_IP "hostname"
# 预期: 返回 ECS 主机名,无密码提示
```

## Rocky Linux 特定的故障排查

### 问题 1: SELinux 阻止服务启动

**症状**: `systemctl start diting` 失败,日志显示 `Permission denied`

**解决**:
```bash
# 查看 SELinux 审计日志
sudo ausearch -m avc -ts recent | grep diting

# 生成 SELinux 策略(如果需要)
sudo ausearch -m avc -ts recent | audit2allow -M diting_custom
sudo semodule -i diting_custom.pp
```

### 问题 2: 端口 8000 无法绑定

**症状**: 服务启动失败,错误信息 `Permission denied` on port 8000

**解决**:
```bash
# 添加端口到 SELinux 允许列表
sudo semanage port -a -t http_port_t -p tcp 8000

# 或临时允许
sudo setsebool -P httpd_can_network_connect 1
```

### 问题 3: Firewalld 阻止连接

**症状**: 外部无法访问应用端口

**解决**:
```bash
# 检查当前规则
sudo firewall-cmd --list-all

# 添加端口
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

### 问题 4: Python 3.12 未找到

**症状**: `python3.12: command not found`

**解决**:
```bash
# 确保 EPEL 仓库启用
sudo dnf install -y epel-release

# 搜索可用的 Python 版本
dnf search python3.12

# 如果 EPEL 中没有,使用源码编译(参考上文)
```

## 性能优化

### 1. 调整系统限制

```bash
# 编辑 limits 配置
sudo vi /etc/security/limits.conf

# 添加:
deploy soft nofile 65536
deploy hard nofile 65536

# 验证(需要重新登录)
su - deploy -c "ulimit -n"
```

### 2. 内核参数调优

```bash
# 编辑 sysctl 配置
sudo vi /etc/sysctl.d/99-diting.conf

# 添加:
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.ip_local_port_range = 10000 65535

# 应用配置
sudo sysctl -p /etc/sysctl.d/99-diting.conf
```

## 相关文档

- [CI/CD 快速上手](../../specs/005-github-ci-aliyun-deploy/quickstart.md)
- [环境差异说明](./environment-differences.md)
- [act 本地 CI 工具](./act-setup.md)
- [Rocky Linux 官方文档](https://docs.rockylinux.org/)
- [SELinux 用户指南](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/9/html/using_selinux/index)
