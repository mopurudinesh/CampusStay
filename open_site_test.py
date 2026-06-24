from selenium import webdriver
import time

driver = webdriver.Chrome()

driver.get("http://127.0.0.1:8000")

print(driver.title)

time.sleep(5)

driver.quit()