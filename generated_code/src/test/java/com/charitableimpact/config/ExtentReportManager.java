package com.charitableimpact.config;

import com.aventstack.extentreports.ExtentReports;
import com.aventstack.extentreports.reporter.ExtentSparkReporter;

import java.io.File;

public class ExtentReportManager {
    private static ExtentReports extent;

    public static ExtentReports getInstance() {
        if (extent == null) {
            // Ensure the directory exists
            File reportDir = new File("generated_code/test-output");
            if (!reportDir.exists()) {
                reportDir.mkdirs(); // Creates the folder if it doesn't exist
            }
            ExtentSparkReporter sparkReporter = new ExtentSparkReporter("generated_code/test-output/ExtentReport.html");
        
            extent = new ExtentReports();
            extent.attachReporter(sparkReporter);
        }
        return extent;
    }
}
