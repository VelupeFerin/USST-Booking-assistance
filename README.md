# USST Booking assistance

上海理工大学（USST）运动场预定辅助系统

此说明文档正在更新

！注意，这个项目的代码非常混乱，不要学习它！

## 最新消息

由于目标网站页面更改，场地信息由文本转为canva图像，旧的识别方式不可用，系统暂时不可用



# 基本功能概述

使用selenium模拟浏览器操作，提供较好的隐蔽性

可多人同时预订，通过cookie配置多人账号。使用HTML页面使选定场地可视化

预订失败则寻找同一时间的其他场次预订；预订成功后，导出场地二维码



# 软件包

PIL

selenium

undetected_chromedriver

