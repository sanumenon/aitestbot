package com.charitableimpact;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.FindBy;
import org.openqa.selenium.support.PageFactory;

public class GroupEditPage {
    private WebDriver driver;

    @FindBy(id = "group_name")
    private WebElement groupNameInput;

    @FindBy(xpath = "//button[contains(text(),'Update Group')]")
    private WebElement updateGroupButton;

    public GroupEditPage(WebDriver driver) {
        this.driver = driver;
        PageFactory.initElements(driver, this);
    }

    public void updateGroupName(String newName) {
        groupNameInput.clear();
        groupNameInput.sendKeys(newName);
    }

    public void clickUpdateGroupButton() {
        updateGroupButton.click();
    }

    public String getUpdatedGroupName() {
        return groupNameInput.getAttribute("value");
    }
}