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
import org.testng.annotations.Test;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;
import io.github.bonigarcia.wdm.WebDriverManager;
import java.time.Duration;
import org.openqa.selenium.support.ui.WebDriverWait;
import com.aventstack.extentreports.ExtentReports;
import com.aventstack.extentreports.ExtentTest;
import com.aventstack.extentreports.Status;
import com.charitableimpact.config.ExtentReportManager;

public class LoginTest {
    private WebDriver driver;
    private WebDriverWait wait;
    ExtentTest test;

    @BeforeClass
    public void setUp() {
        WebDriverManager.chromedriver().setup();
        ChromeOptions options = new ChromeOptions();
        options.addArguments("--start-maximized");
        driver = new ChromeDriver(options);
        wait = new WebDriverWait(driver, Duration.ofSeconds(10));
    }

    @Test
    public void loginTest() {
        ExtentTest test = ExtentReportManager.createTest("Login Test");

        driver.get("https://my.charitableimpact.com/users/login");
        LoginPage loginPage = new LoginPage(driver);

        test.log(Status.INFO, "Entering email and password");
        loginPage.enterEmail("menon.sanu@gmail.com");
        loginPage.enterPassword("Test123#");

        test.log(Status.INFO, "Clicking on Login button");
        loginPage.clickLoginButton();

        // Add verification steps here
    }

    @AfterClass
    public void tearDown() {
        driver.quit();
    }
}