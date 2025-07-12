package com.charitableimpact;

import org.openqa.selenium.*;
import org.openqa.selenium.support.*;
import org.openqa.selenium.By;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;
import org.openqa.selenium.support.ui.Select;
import org.openqa.selenium.interactions.Actions;
import java.time.Duration;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.FindBy;
import org.openqa.selenium.support.PageFactory;

public class GroupEditPage {
    WebDriver driver;

    @FindBy(id = "group-name")
    private WebElement groupNameField;

    @FindBy(xpath = "//button[contains(text(),'Save')]")
    private WebElement saveButton;

    public GroupEditPage(WebDriver driver) {
        this.driver = driver;
        PageFactory.initElements(driver, this);
    }

    public void editGroupName(String newName) {
        groupNameField.clear();
        groupNameField.sendKeys(newName);
    }

    public void clickSaveButton() {
        saveButton.click();
    }
}