package com.charitableimpact;

import org.openqa.selenium.*;
import org.openqa.selenium.chrome.*;
import org.testng.*;
import org.testng.annotations.*;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;
import org.testng.Assert;
import org.testng.asserts.SoftAssert;
import com.aventstack.extentreports.*;
import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import org.openqa.selenium.OutputType;
import org.openqa.selenium.TakesScreenshot;
import org.openqa.selenium.JavascriptExecutor;
import org.openqa.selenium.By;
import java.time.Duration;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.Test;
import com.aventstack.extentreports.ExtentReports;
import com.aventstack.extentreports.ExtentTest;
import com.aventstack.extentreports.Status;
import com.charitableimpact.config.ExtentReportManager;
import io.github.bonigarcia.wdm.WebDriverManager;

public class GroupEditTest {
    private WebDriver driver;
    ExtentTest test;

    @BeforeClass
    public void setUp() {
        ExtentReports extent = ExtentReportManager.getExtent();
        test = ExtentReportManager.createTest("Group Edit Test");

        WebDriverManager.chromedriver().setup();
        driver = new ChromeDriver();
        driver.manage().window().maximize();
        driver.get("https://my.charitableimpact.com/users/login");

        // Login before navigating to group edit page
        LoginPage loginPage = new LoginPage(driver);
        loginPage.enterEmail("menon.sanu@gmail.com");
        loginPage.enterPassword("Test123#");
        loginPage.clickLoginButton();
    }

    @Test
    public void testEditGroupName() {
        driver.get("https://my.charitableimpact.com/groups/test-group-by-sanu-updated-by-nandu/edit");

        GroupEditPage groupEditPage = new GroupEditPage(driver);

        test.log(Status.INFO, "Editing group name to Cheehoo");
        groupEditPage.editGroupName("Cheehoo");

        test.log(Status.INFO, "Clicking on Save button");
        groupEditPage.clickSaveButton();

        // Add assertions or further steps as needed
    }

    // Add @AfterClass method to quit driver and flush extent reports
}