# K3C_info
#### 此插件基于1.6的官改版本！
##### homeassistant的K3C插件，可以获取路由器的相关设备信息，包含以下内容：
nameList = ["2.4G 温度","2.4G 功率","5G 温度","内存使用率","CPU1 温度","5G 功率","CPU使用率","CPU2 温度","下载速度","上传速度","2.4G设备在线数量","5G设备在线数量","lan设备在线数量"]
#### 用法:
##### 将插件文件夹拷贝至custom_components目录中，重启后在configuration.yaml中填写以下内容：
sensor:  
&ensp;\-&ensp;platform: K3C_info  
&ensp;&ensp;&ensp;host: 192.168.2.1  
&ensp;&ensp;&ensp;password: ***  
&ensp;&ensp;&ensp;username: admin
