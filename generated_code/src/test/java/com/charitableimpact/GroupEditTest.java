package com.charitableimpact;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.testng.Assert;
import org.testng.annotations.AfterClass;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.Test;
import java.util.concurrent.TimeUnit;

public class GroupEditTest {
    private WebDriver driver;
    private String baseUrl = "https://my.charitableimpact.com/groups/test-group-by-sanu-updated-by-nandu/edit";

    @BeforeClass
    public void setUp() {
        WebDriverManager.chromedriver().setup();
        driver = new ChromeDriver();
        driver.manage().window().maximize();
        driver.manage().timeouts().implicitlyWait(10, TimeUnit.SECONDS);
        driver.get(baseUrl);
    }

    @Test(dependsOnMethods = "loginTest")
    public void navigateToGroupEditPage() {
        ExtentReportManager.createTest("Navigate to Group Edit Page Test");
        // Add navigation steps to the edit page
    }

    @Test(dependsOnMethods = "navigateToGroupEditPage")
    public void updateGroupNameTest() {
        ExtentReportManager.createTest("Update Group Name Test");
        GroupEditPage groupEditPage = new GroupEditPage(driver);
        groupEditPage.updateGroupName("Cheehoo");
        groupEditPage.clickUpdateGroupButton();
        // Add verification steps here
    }

    @Test(dependsOnMethods = "updateGroupNameTest")
    public void validateUpdatedGroupNameTest() {
        ExtentReportManager.createTest("Validate Updated Group Name Test");
        GroupEditPage groupEditPage = new GroupEditPage(driver);
        String updatedGroupName = groupEditPage.getUpdatedGroupName();
        Assert.assertEquals(updatedGroupName, "Cheehoo", "Group name update validation failed.");
    }

    @AfterClass
    public void tearDown() {
        driver.quit();
        ExtentReportManager.flush();
    }
}