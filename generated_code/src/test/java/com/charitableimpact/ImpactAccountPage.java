package com.charitableimpact;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.FindBy;
import org.openqa.selenium.support.PageFactory;

public class ImpactAccountPage {
    private WebDriver driver;

    @FindBy(id = "inviteButton")
    private WebElement inviteButton;

    public ImpactAccountPage(WebDriver driver) {
        this.driver = driver;
        PageFactory.initElements(driver, this);
    }

    public void clickInviteButton() {
        inviteButton.click();
    }
}