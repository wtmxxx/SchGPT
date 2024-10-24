# 打开本地的data/news.json文件
def trim_news_data(file_path: str, length: int = 100):
    """
    从`news.json`文件中截取指定长度的数据记录，并保存到`news.json`文件中
    :param length: 截取长度
    """
    import json

    with open(file_path, 'r') as file:
        data = json.load(file)
    dict_list = data['data'][:length]
    data['data'] = dict_list
    with open(file_path, 'w') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    trim_news_data(file_path='data/raw/cumt_news.json', length=1000)
