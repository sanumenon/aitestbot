package com.charitableimpact.config;

import com.aventstack.extentreports.ExtentReports;
import com.aventstack.extentreports.ExtentTest;
import com.aventstack.extentreports.reporter.ExtentSparkReporter;

import java.io.File;

public class ExtentReportManager {
    private static ExtentReports extent;
    private static ThreadLocal<ExtentTest> testThread = new ThreadLocal<>();

    static {
        File reportDir = new File("generated_code/test-output");
        if (!reportDir.exists()) {
            reportDir.mkdirs();
        }
        ExtentSparkReporter sparkReporter = new ExtentSparkReporter("generated_code/test-output/ExtentReport.html");
        extent = new ExtentReports();
        extent.attachReporter(sparkReporter);
    }

    public static ExtentReports getExtent() {
        return extent;
    }

    public static ExtentTest createTest(String testName) {
        ExtentTest test = extent.createTest(testName);
        testThread.set(test);
        return test;
    }

    public static ExtentTest getTest() {
        return testThread.get();
    }

    public static void flush() {
        if (extent != null) {
            extent.flush();
        }
    }
}
