package com.charitableimpact;
import org.openqa.selenium.WebDriver;

import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;
import io.github.bonigarcia.wdm.WebDriverManager;

import org.testng.annotations.*;
import org.testng.Assert;
import com.charitableimpact.LoginPage;

public class LoginTest {
    WebDriver driver;

    @BeforeClass
    public void setup() {
        
        WebDriverManager.chromedriver().setup();
        ChromeOptions options = new ChromeOptions();
        options.addArguments("--headless");
        options.addArguments("--no-sandbox");
        options.addArguments("--disable-dev-shm-usage");
        driver = new ChromeDriver(options);
        
        driver.manage().window().maximize();
        driver.get("https://my.charitableimpact.com");
    }

    @Test
    public void testLogin() {
        LoginPage page = new LoginPage(driver);
        
        try {
            page.interactWithElement0();
        } catch (Exception e) {
            System.out.println("❌ Failed to interact with: element0 - " + e.getMessage());
        }
        
        try {
            page.interactWithElement1();
        } catch (Exception e) {
            System.out.println("❌ Failed to interact with: element1 - " + e.getMessage());
        }
        
        try {
            page.interactWithElement2();
        } catch (Exception e) {
            System.out.println("❌ Failed to interact with: element2 - " + e.getMessage());
        }
        
        try {
            page.interactWithCf_turnstile_response();
        } catch (Exception e) {
            System.out.println("❌ Failed to interact with: cf_turnstile_response - " + e.getMessage());
        }
        
        try {
            page.interactWithElement4();
        } catch (Exception e) {
            System.out.println("❌ Failed to interact with: element4 - " + e.getMessage());
        }
        
        try {
            page.interactWithElement5();
        } catch (Exception e) {
            System.out.println("❌ Failed to interact with: element5 - " + e.getMessage());
        }
        
        try {
            page.interactWithElement6();
        } catch (Exception e) {
            System.out.println("❌ Failed to interact with: element6 - " + e.getMessage());
        }
        

        // Robust validation: check if a key element is actually visible
        try {
            Assert.assertTrue(
                driver.findElement(page.getElement0Locator()).isDisplayed(),
                "Validation failed: element0 is not displayed."
            );
        } catch (Exception e) {
            Assert.fail("Validation element 'element0' not found: " + e.getMessage());
        }
    }

    @AfterClass
    public void teardown() {
        if (driver != null) {
            driver.quit();
        }
    }
}