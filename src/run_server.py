from kitbit.server.webserver import KitbitServer

if __name__ == '__main__':
    KitbitServer().app.run('0.0.0.0', 5058)