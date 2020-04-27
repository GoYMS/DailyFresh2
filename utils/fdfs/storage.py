"""自定义文件存储的方法，修改django自带上传方法"""

from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client


class FdfsStorage(Storage):
    """fast dfs 文件存储类"""

    def _open(self,name,mode='rd'):
        """打开文件的时候使用"""
        pass

    def _save(self, name, content):
        """
        保存文件的时候使用
            name: 选择上传文件的名字
            content:包含你上传文件内容的file的对象
        """

        # 创建一个Fdfs client对象,指定一个client文件
        client = Fdfs_client('utils/fdfs/client.conf')

        # 上传文件到fast dfs系统中
        res = client.upload_appender_by_buffer(content.read())
        # 返回值包含以下内容
        # dict
        # {
        #     'Group name': group_name,
        #     'Remote file_id': remote_file_id,
        #     'Status': 'Upload successed.',
        #     'Local file name': '',
        #     'Uploaded size': upload_size,
        #     'Storage IP': storage_ip
        # }

        if res.get('Status') !='Upload successed.':
            # 上传失败
            raise Exception('上传文件失败')
        # 获取返回的文件的id
        filename = res.get('Remote file_id')
        return filename

    def exists(self, name):
        """判断文件是否可用"""
        return False

    def url(self, name):
        """返回文件的url"""
        # 此处是使用nginx代理的，所以端口号与配置nginx的时候一样，ip是前边配置
        # 文件的时候写的，我写的是本机的，所以使用127.0.0.1也可以
        return 'http://127.0.0.1:8888/'+name



