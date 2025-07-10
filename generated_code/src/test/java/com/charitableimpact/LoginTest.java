package com.charitableimpact;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.testng.annotations.AfterClass;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.Test;
import java.util.concurrent.TimeUnit;

public class LoginTest {
    private WebDriver driver;
    private String baseUrl = "https://my.charitableimpact.com/users/login";

    @BeforeClass
    public void setUp() {
        WebDriverManager.chromedriver().setup();
        driver = new ChromeDriver();
        driver.manage().window().maximize();
        driver.manage().timeouts().implicitlyWait(10, TimeUnit.SECONDS);
        driver.get(baseUrl);
    }

    @Test
    public void loginTest() {
        ExtentReportManager.createTest("Login Test");
        LoginPage loginPage = new LoginPage(driver);
        loginPage.enterEmail("menon.sanu@gmail.com");
        loginPage.enterPassword("Test123#");
        loginPage.clickLoginButton();
        // Add verification steps here
    }

    @AfterClass
    public void tearDown() {
        driver.quit();
        ExtentReportManager.flush();
    }
}