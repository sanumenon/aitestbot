package com.charitableimpact;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.testng.annotations.AfterClass;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.Test;
import java.time.Duration;
import static org.testng.Assert.assertEquals;

import com.aventstack.extentreports.ExtentReports;
import com.aventstack.extentreports.ExtentTest;
import com.aventstack.extentreports.Status;
import com.charitableimpact.config.ExtentReportManager;
import io.github.bonigarcia.wdm.WebDriverManager;

public class InviteToImpactAccountTest {
    private WebDriver driver;
    private String baseURL = "https://my.charitableimpact.com";
    private String email = "menon.sanu@gmail.com";
    private String password = "examplePassword";

    @BeforeClass
    public void setUp() {
        WebDriverManager.chromedriver().setup();
        driver = new ChromeDriver();
        driver.manage().window().maximize();
        driver.manage().timeouts().implicitlyWait(Duration.ofSeconds(10));
    }

    @Test
    public void testInviteToImpactAccount() {
        ExtentTest test = ExtentReportManager.createTest("Invite to Impact Account Test");

        driver.get(baseURL);

        LoginPage loginPage = new LoginPage(driver);
        loginPage.enterEmail(email);
        loginPage.enterPassword(password);
        loginPage.clickLoginButton();
        test.log(Status.INFO, "Logged in successfully");

        // Navigation to Impact Account page and invite functionality
        ImpactAccountPage impactAccountPage = new ImpactAccountPage(driver);
        impactAccountPage.clickInviteButton();
        test.log(Status.INFO, "Clicked on Invite button in Impact Account");

        // Add verification or further actions here
    }

    @AfterClass
    public void tearDown() {
        driver.quit();
        ExtentReportManager.flush();
    }
}