import base64
import logging
import requests
import json
import hashlib
import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    DATA_RATE_BYTES_PER_SECOND,
    DATA_RATE_KILOBYTES_PER_SECOND,
    DATA_RATE_MEGABYTES_PER_SECOND,
    DATA_RATE_GIGABYTES_PER_SECOND,
    TEMP_CELSIUS,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    PERCENTAGE

)

import homeassistant.helpers.config_validation as cv
_LOGGER = logging.getLogger(__name__)

infoList = ["temp24","power24","temp5","ram_used","cputemp1","power5","cpu_used","cputemp2","download_speed",
            "upload_speed","online_24G","online_5G","online_lan"]
nameList = ["2.4G 温度","2.4G 功率","5G 温度","内存使用率","CPU1 温度","5G 功率","CPU使用率","CPU2 温度","下载速度",
            "上传速度","2.4G设备在线数量","5G设备在线数量","lan设备在线数量"]

units = [DATA_RATE_BYTES_PER_SECOND, DATA_RATE_KILOBYTES_PER_SECOND, DATA_RATE_MEGABYTES_PER_SECOND, DATA_RATE_GIGABYTES_PER_SECOND]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_USERNAME): cv.string
})

stoken = ""

def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:

    entities = []
    for i in infoList:
        entities.append(K3CDevice(config, i, nameList[infoList.index(i)]))
    add_entities(entities)

class K3CDeviceLogin:
    def __init__(self,host,username,password):
        self.host = host
        self.username =  username
        self.password = password
        self.data = self.getK3CInfo()

    def getK3CInfo(self):
        headers = {
            "Content-Type": "application/json"
        }

        loginUrl = "http://{}/cgi-bin/".format(self.host)

        passwordString = self.password.encode();
        result = base64.b64encode(passwordString)

        security = {'security': {'login': {'username': 'tab', 'password': result.decode()}}}
        r = requests.post(loginUrl, data=self.buildPostData("set", security), headers=headers)
        responseJson = json.loads(r.text)
        stoken = responseJson['module']['security']['login']['stok']

        getDeviceListUrl = "http://{}/cgi-bin/stok={}/data".format(self.host, stoken)
        infoArgs = {'device': {'info': None},'network':{'lan':None,'wan_status':None},'device_manage':{'device_num':None}}
        r = requests.post(getDeviceListUrl, data=self.buildPostData("get", infoArgs), headers=headers)

        result = json.loads(r.text)
        if (result['error_code'] == 0):
            self.info = result['module']['device']['info']
            self.info['ram_used'] = "%.2f" % ((int(self.info['used_ram']) / int(self.info['total_ram'])) * 100)
            self.lan = result['module']['network']['wan_status']
            self.num = result['module']['device_manage']['device_num']

    def buildPostData(self, method, args):
        postInfo = {}
        data = json.loads(json.dumps(postInfo))
        data['method'] = method
        data['_deviceType'] = 'PC'
        data['module'] = args
        postInfo = json.dumps(data)
        print(postInfo)
        return postInfo

class K3CDevice(K3CDeviceLogin,SensorEntity):
    def __init__(self,config, attrName, infoName ):
        self.host = config[CONF_HOST]
        self.username = config[CONF_USERNAME]
        self.password = config[CONF_PASSWORD]
        self._name = infoName
        self._attr_name = attrName

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        return hashlib.md5((str(self._name + self._attr_name)).encode(encoding='UTF-8')).hexdigest()

    def update(self) -> None:
        self.getK3CInfo()
        if "temp" in self._attr_name:
            self._attr_native_unit_of_measurement = TEMP_CELSIUS
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_value = int(str(self.info[self._attr_name]).split("%")[0])
        if "power" in self._attr_name:
            self._attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
            self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
            self._attr_native_value = int(str(self.info[self._attr_name]).split("%")[0])
        if "used" in self._attr_name:
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_native_value = self.info[self._attr_name]
        if "speed" in self._attr_name:
            result = self.hum_convert(int(self.lan[self._attr_name]))
            self._attr_native_unit_of_measurement = units[result[1]]
            self._attr_device_class = SensorDeviceClass.SPEED
            self._attr_native_value = result[0]
        if "online" in self._attr_name:
            self._attr_native_unit_of_measurement = "台"
            self._attr_device_class = SensorDeviceClass.CURRENT
            self._attr_native_value = int(self.num[self._attr_name])

    def hum_convert(self,value):
        size = 1024.0
        list = []
        for i in range(len(units)):
            if (value / size) < 1:
                list.append("%.2f" % (value))
                list.append(i)
                return list
            value = value / size