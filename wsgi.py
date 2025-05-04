# 直接导入 app.py 中的 app 变量
import app as flask_app

# 获取 Flask 应用程序实例
application = flask_app.app

if __name__ == '__main__':
    from waitress import serve
    serve(application, host='0.0.0.0', port=5000)
