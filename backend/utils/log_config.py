import logging
class Log:
    def __init__(self,name:str,level:str):          #name是日志器名字，无所谓，    level是日志器的能启用的错误程度下限
        self.logName = logging.getLogger(name)
        self.logName.setLevel(eval( f'logging.{level.upper()}') )
        self.log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                                          , datefmt='%Y-%m-%d %H:%M:%S'  # 定义时间的格式
                                          )
    def logConsol(self):
        console_handler = logging.StreamHandler()  # 实例化一个输出到控制台的handerl对象
        console_handler.setFormatter(self.log_formatter) # handerl绑定输出格式
        self.logName.addHandler(console_handler)

    def logFile(self,file:str):
        file_handler = logging.FileHandler('logs/'+file, mode='a',encoding='utf-8')  # 实例化一个输出到文件的handlers对象，默认是追加模式
        if "error" in file:                 #判断是不是存在error相关的文件
            file_handler.setLevel(logging.ERROR)        #是的话，错误级别就设置为error，过滤掉低危害错误
        else:
            file_handler.setLevel(logging.DEBUG)        #默认存储DEBUG以上的错误到另一个文件
        file_handler.setFormatter(self.log_formatter)  # handerl绑定输出格式
        self.logName.addHandler(file_handler)

    def message(self,lv:str,mes:str):               #这边的lv才是写入的级别  mes 是写入的信息
        lv = lv.lower()
        if lv == 'debug':
            self.logName.debug( mes )
        elif lv == 'info':
            self.logName.info(mes)
        elif lv == 'warning':
            self.logName.warning(mes)
        elif lv == 'error':
            self.logName.error(mes)
        elif lv == 'critical':
            self.logName.critical(mes)
        else:
            print('输入的日志级别异常！')

logger = Log('back_log','debug')
logger.logFile('debug.log')
logger.logFile('error.log')

