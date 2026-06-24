from selenium import webdriver
from selenium.webdriver.common.by import By
import time

driver = webdriver.Chrome()

driver.get("http://127.0.0.1:8000/login/")

# Enter credentials
driver.find_element(By.ID, "username").send_keys("192211706")
driver.find_element(By.ID, "password").send_keys("Dinesh@2004")

# Click login
driver.find_element(By.ID, "login-submit-btn").click()

# Wait for redirect
time.sleep(15)

print("Current URL:", driver.current_url)

driver.quit()