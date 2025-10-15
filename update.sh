#!/bin/bash

# 切换到项目目录
cd /root/code/coin

# 拉取最新代码
git pull

# 重启服务
supervisorctl restart coin