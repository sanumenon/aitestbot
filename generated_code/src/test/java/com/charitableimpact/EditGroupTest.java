package com.charitableimpact;

import org.openqa.selenium.*;
import org.openqa.selenium.chrome.*;
import org.testng.*;
import org.testng.annotations.*;
import org.openqa.selenium.support.ui.ExpectedConditions;
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
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.testng.annotations.AfterClass;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.Test;
import io.github.bonigarcia.wdm.WebDriverManager;
import org.openqa.selenium.chrome.ChromeOptions;
import org.openqa.selenium.support.ui.WebDriverWait;
import java.time.Duration;
import com.aventstack.extentreports.ExtentReports;
import com.aventstack.extentreports.ExtentTest;
import com.aventstack.extentreports.Status;
import com.charitableimpact.config.ExtentReportManager;

public class EditGroupTest {
    private WebDriver driver;
    private WebDriverWait wait;
    private ExtentReports extent;
    private ExtentTest test;

    @BeforeClass
    public void setup() {
        WebDriverManager.chromedriver().setup();
        ChromeOptions options = new ChromeOptions();
        options.addArguments("--start-maximized");
        driver = new ChromeDriver(options);
        wait = new WebDriverWait(driver, Duration.ofSeconds(10));
        extent = ExtentReportManager.getExtent();
    }

    @Test
    public void editGroupTest() {
        test = ExtentReportManager.createTest("Edit Group Test");
        test.log(Status.INFO, "Starting Edit Group Test");

        LoginPage loginPage = new LoginPage(driver);
        loginPage.login("menon.sanu@gmail.com", "Test123#");
        test.log(Status.INFO, "Logged in successfully");

        String groupEditUrl = "https://my.charitableimpact.com/groups/test-group-by-sanu-updated-by-nandu/edit";
        driver.get(groupEditUrl);
        test.log(Status.INFO, "Navigated to Group Edit Admin Page");

        GroupEditPage groupEditPage = new GroupEditPage(driver);
        groupEditPage.editGroupName("Cheehoo");
        test.log(Status.INFO, "Edited the group name to Cheehoo");

        groupEditPage.saveGroup();
        test.log(Status.INFO, "Saved the group");

        // Additional verification steps can be added here

        test.log(Status.INFO, "Edit Group Test completed successfully");
    }

    @AfterClass
    public void tearDown() {
        driver.quit();
        ExtentReportManager.flush();
    }
}