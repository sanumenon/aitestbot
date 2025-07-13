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
    private WebDriver driver;

    @FindBy(id = "group-name")
    private WebElement groupNameInput;

    @FindBy(id = "save-group")
    private WebElement saveGroupButton;

    public GroupEditPage(WebDriver driver) {
        this.driver = driver;
        PageFactory.initElements(driver, this);
    }

    public void editGroupName(String newGroupName) {
        groupNameInput.clear();
        groupNameInput.sendKeys(newGroupName);
    }

    public void saveGroup() {
        saveGroupButton.click();
    }
}