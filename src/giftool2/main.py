
def main():
    # flask
    # from .app import app
    # app.run()
    
    # toga
    from .toga_app import main
    app = main()
    app.main_loop()
    
if __name__ == "__main__":
    main()