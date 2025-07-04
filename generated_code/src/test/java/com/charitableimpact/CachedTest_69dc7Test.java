package com.charitableimpact;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.By;
import org.testng.annotations.*;
import org.testng.asserts.SoftAssert;
import com.aventstack.extentreports.*;
import com.charitableimpact.config.ExtentReportManager;
import com.charitableimpact.CachedTest_69dc7Page;


import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;
import io.github.bonigarcia.wdm.WebDriverManager;


public class CachedTest_69dc7Test {
    public WebDriver driver;
    ExtentReports extent;
    ExtentTest test;

    @BeforeClass
    public void setup() {
        extent = ExtentReportManager.getInstance();
        test = extent.createTest("CachedTest_69dc7 Test");

        
        WebDriverManager.chromedriver().setup();
        ChromeOptions options = new ChromeOptions();
        options.addArguments("--headless", "--no-sandbox", "--disable-dev-shm-usage");
        driver = new ChromeDriver(options);
        

        driver.manage().window().maximize();
        driver.get("https://my.charitableimpact.com");
    }

    @Test
    public void testCachedTest_69dc7() {
        SoftAssert softAssert = new SoftAssert();
        CachedTest_69dc7Page page = new CachedTest_69dc7Page(driver);

        

        

        softAssert.assertAll();
    }

    @AfterClass
    public void teardown() {
        if (driver != null) {
            driver.quit();
        }
        extent.flush();
    }
}