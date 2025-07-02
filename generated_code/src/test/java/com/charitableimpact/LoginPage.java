package com.charitableimpact;
import org.openqa.selenium.*;
import org.openqa.selenium.support.ui.Select;

public class LoginPage {
    WebDriver driver;

    public LoginPage(WebDriver driver) {
        this.driver = driver;
    }

    
    By element0Locator = By.xpath("/html[1]/body[1]/section[1]/div[1]/div[1]/div[1]/a[1]");

    public void interactWithElement0() {
        
        WebElement el = driver.findElement(element0Locator);
        el.clear();
        el.sendKeys("Test input");
        
        ((JavascriptExecutor)driver).executeScript("arguments[0].scrollIntoView(true);", driver.findElement(element0Locator));
    }

    public By getElement0Locator() {
        return element0Locator;
    }
    
    By element1Locator = By.xpath("//*[@id='xEqtR4']");

    public void interactWithElement1() {
        
        WebElement el = driver.findElement(element1Locator);
        el.clear();
        el.sendKeys("Test input");
        
        ((JavascriptExecutor)driver).executeScript("arguments[0].scrollIntoView(true);", driver.findElement(element1Locator));
    }

    public By getElement1Locator() {
        return element1Locator;
    }
    
    By element2Locator = By.xpath("//*[@id='MwRA1']");

    public void interactWithElement2() {
        
        WebElement el = driver.findElement(element2Locator);
        el.clear();
        el.sendKeys("Test input");
        
        ((JavascriptExecutor)driver).executeScript("arguments[0].scrollIntoView(true);", driver.findElement(element2Locator));
    }

    public By getElement2Locator() {
        return element2Locator;
    }
    
    By cf_turnstile_responseLocator = By.xpath("//*[@id='cf-chl-widget-g5tyr_response']");

    public void interactWithCf_turnstile_response() {
        
        WebElement el = driver.findElement(cf_turnstile_responseLocator);
        el.clear();
        el.sendKeys("Test input");
        
        ((JavascriptExecutor)driver).executeScript("arguments[0].scrollIntoView(true);", driver.findElement(cf_turnstile_responseLocator));
    }

    public By getCf_turnstile_responseLocator() {
        return cf_turnstile_responseLocator;
    }
    
    By element4Locator = By.xpath("//*[@id='lYDM4']");

    public void interactWithElement4() {
        
        WebElement el = driver.findElement(element4Locator);
        el.clear();
        el.sendKeys("Test input");
        
        ((JavascriptExecutor)driver).executeScript("arguments[0].scrollIntoView(true);", driver.findElement(element4Locator));
    }

    public By getElement4Locator() {
        return element4Locator;
    }
    
    By element5Locator = By.xpath("//*[@id='xiGRv0']");

    public void interactWithElement5() {
        
        WebElement el = driver.findElement(element5Locator);
        el.clear();
        el.sendKeys("Test input");
        
        ((JavascriptExecutor)driver).executeScript("arguments[0].scrollIntoView(true);", driver.findElement(element5Locator));
    }

    public By getElement5Locator() {
        return element5Locator;
    }
    
    By element6Locator = By.xpath("//*[@id='cItN1']");

    public void interactWithElement6() {
        
        WebElement el = driver.findElement(element6Locator);
        el.clear();
        el.sendKeys("Test input");
        
        ((JavascriptExecutor)driver).executeScript("arguments[0].scrollIntoView(true);", driver.findElement(element6Locator));
    }

    public By getElement6Locator() {
        return element6Locator;
    }
    
}