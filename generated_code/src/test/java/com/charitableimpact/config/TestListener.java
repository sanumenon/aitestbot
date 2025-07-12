package com.charitableimpact.config;

import com.aventstack.extentreports.ExtentReports;
import com.aventstack.extentreports.ExtentTest;
import com.aventstack.extentreports.Status;
import com.aventstack.extentreports.reporter.ExtentSparkReporter;

import java.io.File;
import java.io.IOException;
import org.openqa.selenium.*;
import java.io.File;
import java.io.IOException;
import org.apache.commons.io.FileUtils;


import org.apache.commons.io.FileUtils;
import org.openqa.selenium.OutputType;
import org.openqa.selenium.TakesScreenshot;
import org.openqa.selenium.WebDriver;
import org.testng.ITestContext;
import org.testng.ITestListener;
import org.testng.ITestResult;

public class TestListener implements ITestListener {
    private static ExtentReports extent = ExtentReportManager.getExtent();
    private static ThreadLocal<ExtentTest> test = new ThreadLocal<>();

    @Override
    public void onTestStart(ITestResult result) {
        ExtentTest extentTest = extent.createTest(result.getMethod().getMethodName());
        test.set(extentTest);
    }

    @Override
    public void onTestSuccess(ITestResult result) {
        test.get().log(Status.PASS, "✅ Test passed");
    }

   @Override
public void onTestFailure(ITestResult result) {
    test.get().log(Status.FAIL, "❌ Test failed: " + result.getThrowable());

    Object testClass = result.getInstance();;
    WebDriver driver = null;

    try {
        driver = (WebDriver) result.getTestClass()
            .getRealClass()
            .getDeclaredField("driver")
            .get(testClass);
    } catch (Exception e) {
        test.get().log(Status.WARNING, "⚠️ Unable to access WebDriver for screenshot: " + e.getMessage());
        return;
    }

    if (driver != null) {
        String screenshotPath = takeScreenshot(driver, result.getMethod().getMethodName());
        try {
            test.get().addScreenCaptureFromPath(screenshotPath, "📸 Screenshot on Failure");
        } catch (Exception e) {
            test.get().log(Status.WARNING, "⚠️ Could not attach screenshot: " + e.getMessage());
        }
    }
}


    @Override
    public void onTestSkipped(ITestResult result) {
        test.get().log(Status.SKIP, "⚠️ Test skipped: " + result.getThrowable());
    }

    @Override
    public void onFinish(ITestContext context) {
        extent.flush(); // generate report at end
    }

    // Unused but required
    @Override public void onStart(ITestContext context) {}
    @Override public void onTestFailedButWithinSuccessPercentage(ITestResult result) {}
    @Override public void onTestFailedWithTimeout(ITestResult result) {}
    public String takeScreenshot(WebDriver driver, String methodName) {
    String timestamp = new java.text.SimpleDateFormat("yyyyMMdd_HHmmss").format(new java.util.Date());
    String screenshotDir = "generated_code/screenshots";
    String screenshotPath = screenshotDir + "/" + methodName + "_" + timestamp + ".png";

    File src = ((TakesScreenshot) driver).getScreenshotAs(OutputType.FILE);
    File dest = new File(screenshotPath);
    try {
        // Ensure directory exists
        new File(screenshotDir).mkdirs();
        FileUtils.copyFile(src, dest);
    } catch (IOException e) {
        System.err.println("❌ Screenshot failed: " + e.getMessage());
    }
    return screenshotPath;
}

}
