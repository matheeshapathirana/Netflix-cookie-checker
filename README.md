
# Netflix Cookie Checker - Colab Version

**Checks Cookies for validity.**

![Logo](images/netflix_logo.jpg)


# Installation

```cmd
  !git clone https://github.com/matheeshapathirana/Netflix-cookie-checker.git
  !git checkout colab-version
  %cd Netflix-cookie-checker
  !mkdir cookies
  !pip install -r requirements.txt
```
# Usage

1. Upload cookies (Netscape format) to `Netflix-cookie-checker/cookies` folder.

   ***NOTE :*** If you already have json cookies then create a folder named `json_cookies` and upload cookies to that folder then run [main.py](https://github.com/matheeshapathirana/Netflix-cookie-checker/blob/0b04b55e3b1d9bdc35f955d926e794851280d4d0/main.py)
2. Run [cookie_converter.py](https://github.com/matheeshapathirana/Netflix-cookie-checker/blob/b82b684355a80e23f5648e6082090d9cd5332cc3/cookie_converter.py) to convert Netscape cookies to json format.

   `!python3 cookie_converter.py`
3. Run [main.py](https://github.com/matheeshapathirana/Netflix-cookie-checker/blob/0b04b55e3b1d9bdc35f955d926e794851280d4d0/main.py).

    `!python3 main.py`
# For any issues
<a href="https://discord.gg/RSCdKeKB5X"><img src="https://discord.com/api/guilds/1121457935822901278/widget.png?style=banner2"></a>
