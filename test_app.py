import app


def test_app():

    username = 'Pablo'
    password = 1234567

    loginB = app.login()

    assert loginB == 1

test_app()
