import mysql.connector

def conectar():
    return mysql.connector.connect(
        host="iriguchi.proxy.rlwy.net",
        port=41069,
        user="root",
        password="PYqkSyHVQgcLPebywxQItXawgbWlpgur",
        database="railway"
    )
