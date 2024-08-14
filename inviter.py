from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import pickle
import os
import csv
import logging
from utils import wait_for_internet_connection  # Import the new function
from config import INVITED_ATTENDEES_FILE

class LinkedInInviter:
    def __init__(self, driver, event_url, csv_file_path):
        self.driver = driver
        self.event_url = event_url
        self.csv_file_path = csv_file_path
        self.invited_attendees = set()
        self.attendees_selected = 0
        self.load_invited_attendees()

    def load_invited_attendees(self):
        invited_attendees = set()

        # Load from CSV file
        if os.path.exists(self.csv_file_path):
            with open(self.csv_file_path, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                next(reader, None)  # Skip the header
                invited_attendees = set(row[0] for row in reader)  # Read all previously invited names

        self.invited_attendees = invited_attendees

    def save_new_invites(self, new_invites):
        with open(self.csv_file_path, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerows(new_invites)

        # Load from CSV file
        # if os.path.exists(self.csv_file_path):
        #     with open(self.csv_file_path, mode='r', newline='', encoding='utf-8') as file:
        #         reader = csv.reader(file)
        #         invited_attendees = set(row[0] for row in reader)  # Read all previously invited names
        
    def click_invite_list_item(self):
        self.driver.get(self.event_url)
        time.sleep(5)

        try:
            share_button = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, '//span[contains(@class, "align-items-center display-flex")]/ancestor::button'))
            )
            self.driver.execute_script("arguments[0].scrollIntoView();", share_button)
            self.driver.execute_script("arguments[0].click();", share_button)

            invite_list_item = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//ul[@role='menu']/li[1]"))
            )
            self.driver.execute_script("arguments[0].scrollIntoView();", invite_list_item)
            self.driver.execute_script("arguments[0].click();", invite_list_item)
            return True
        except Exception as e:
            logging.error(f"Error interacting with Share or Invite buttons: {e}")
            return False

    def select_profiles_to_invite(self, max_invites=5):
        time.sleep(5)
        global attendees_selected

        try:
            container = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//div[@id='invitee-picker-results-container']"))
            )
            
            new_invites = []
            logging.info("Starting the selection of profiles to invite.")

            while self.attendees_selected < max_invites:
                # Ensure the internet connection is available before proceeding
                wait_for_internet_connection()

                # Click the button to load more profiles first to refresh the page
                try:
                    load_more_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, '//div[@class="display-flex p5"]/button/span[@class="artdeco-button__text"]'))
                    )
                    self.driver.execute_script("arguments[0].click();", load_more_button)
                    logging.info("Clicked the button to load more profiles.")
                    time.sleep(5)  # Allow some time for new profiles to load

                except TimeoutException:
                    logging.warning("Load more button not found. Assuming all profiles are loaded or another issue occurred.")
                    break  # Exit the loop if the button is not found

                # Ensure the internet connection is available before selecting profiles
                wait_for_internet_connection()

                # After loading more profiles, select attendees
                attendee_elements = container.find_elements(By.XPATH, './/input[@aria-selected="false"]')

                for attendee_element in attendee_elements:
                    # Ensure the internet connection is available before each profile selection
                    wait_for_internet_connection()

                    try:
                        invited_status_elements = attendee_element.find_elements(By.XPATH, ".//ancestor::li//div[@class='invitee-picker-connections-result-item__status t-14 t-black--light t-bold mt2']")

                        if invited_status_elements and invited_status_elements[0].text.strip() == "Invited":
                            continue

                        attendee_name_element = attendee_element.find_element(By.XPATH, ".//ancestor::li//div[@class='flex-1 inline-block align-self-center pl2 mr5']/div[1]")
                        attendee_name = attendee_name_element.text.strip()

                        attendee_headline_element = attendee_element.find_element(By.XPATH, ".//ancestor::li//div[@class='flex-1 inline-block align-self-center pl2 mr5']/div[2]")
                        attendee_headline = attendee_headline_element.text.strip()

                        time.sleep(2)

                        if attendee_name not in self.invited_attendees:
                            self.driver.execute_script("arguments[0].click();", attendee_element)

                            if attendee_element.get_attribute("aria-selected") == "true":
                                self.invited_attendees.add(attendee_name)
                                new_invites.append((attendee_name, attendee_headline, time.strftime('%Y-%m-%d %H:%M:%S')))
                                self.attendees_selected += 1

                                logging.info(f"Profile selected: {attendee_name}, Total selected: {self.attendees_selected}")
                        
                        if self.attendees_selected >= max_invites:
                            logging.info(f"Stopping selection. Total profiles selected: {self.attendees_selected}")
                            break

                    except Exception as e:
                        logging.error(f"Encountered an issue with an element: {e}")
                        continue

            self.save_new_invites(new_invites)
            logging.info(f"Finished inviting {self.attendees_selected} profiles.")
            return self.attendees_selected

        except TimeoutException:
            logging.error("Element not found within the given time")
            return 0

    def click_invite_button(self):
        try:
            invite_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '/html/body/div[3]/div/div/div[2]/div/div[2]/div/button/span'))
            )
            self.driver.execute_script("arguments[0].scrollIntoView();", invite_button)
            self.driver.execute_script("arguments[0].click();", invite_button)
            logging.info("Invite button clicked.")

            time.sleep(5)
            
        except Exception as e:
            logging.error(f"Error clicking the Invite button: {e}")

    def invite_attendees(self, max_invites=5):
        self.attendees_selected = 0  # Reset the variable at the start of the method
        if self.click_invite_list_item():
            self.select_profiles_to_invite(max_invites=max_invites)
            if self.attendees_selected > 0:
                self.click_invite_button()
                logging.info(f"Invited {self.attendees_selected} new attendees.")
            else:
                logging.info("No new attendees were selected.")
        else:
            logging.warning("Failed to initiate the invite process.")
