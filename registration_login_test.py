from selenium import webdriver
from selenium.webdriver.common.by import By
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

driver = webdriver.Chrome()

try:
    # =========================
    # OPEN REGISTRATION PAGE
    # =========================

    driver.get("http://127.0.0.1:8000/signup/")
    print("Registration page opened")

    # =========================
    # REGISTRATION FORM
    # =========================

    driver.find_element(By.ID, "username").send_keys("SeleniumTest01")
    time.sleep(1)

    driver.find_element(By.ID, "email").send_keys("seleniumtest01@gmail.com")
    time.sleep(1)

    driver.find_element(By.ID, "full_name").send_keys("Selenium Test User")
    time.sleep(1)

    driver.find_element(By.ID, "student_id").send_keys("STU90001")
    time.sleep(1)

    driver.find_element(By.ID, "phone").send_keys("9876543210")
    time.sleep(1)

    driver.find_element(By.ID, "gender").send_keys("Male")
    time.sleep(1)

    driver.find_element(By.ID, "course").send_keys("B.E.")
    time.sleep(1)

    driver.find_element(By.ID, "department").send_keys("Computer Science")
    time.sleep(1)

    driver.find_element(By.ID, "year_of_study").send_keys("4")
    time.sleep(1)

    driver.find_element(By.ID, "batch_start").send_keys("2022")
    time.sleep(1)

    driver.find_element(By.ID, "batch_end").send_keys("2026")
    time.sleep(1)

    driver.find_element(By.ID, "parent_contact").send_keys("9876543211")
    time.sleep(1)

    driver.find_element(By.ID, "address").send_keys("Chennai, Tamil Nadu, India")
    time.sleep(1)

    driver.find_element(By.ID, "password").send_keys("Test@12345")
    time.sleep(1)

    driver.find_element(By.ID, "confirm_password").send_keys("Test@12345")
    time.sleep(1)

    print("Registration form filled")
    input("All fields filled. Press Enter to click Register...")

    # =========================
    # CLICK REGISTER
    # =========================

    # Wait until login page loads completely
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "username"))
    )

    print("Login page loaded")

    # Find elements again on the new page
    username_box = driver.find_element(By.ID, "username")
    password_box = driver.find_element(By.ID, "password")

    username_box.clear()
    password_box.clear()

    username_box.send_keys("STU90001")
    time.sleep(1)

    password_box.send_keys("Test@12345")
    time.sleep(1)

    print("Credentials entered")

    driver.find_element(By.ID, "login-submit-btn").click()

    print("Login clicked")

    # Wait for dashboard
    WebDriverWait(driver, 20).until(
        lambda d: "/dashboard/" in d.current_url
    )

    print("Dashboard opened")
    print("URL:", driver.current_url)

except Exception as e:
    print(f"An error occurred: {e}")