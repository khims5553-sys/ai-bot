package com.nseai.bot;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.CookieManager;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;

public class MainActivity extends Activity {

    private static final String APP_URL = "https://dashboardpy-fxqfhb5xeacbtk4vue38j2.streamlit.app";

    private WebView web;
    private ProgressBar progress;
    private LinearLayout errorPanel;
    private TextView errorMessage;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        try {
            createScreen();
            configureWebView();
            loadApp();
        } catch (Exception e) {
            showError("App start nahi ho paya: " + safeMessage(e));
        }
    }

    private void createScreen() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.WHITE);

        progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progress.setIndeterminate(false);
        root.addView(progress, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(4)));

        web = new WebView(this);
        root.addView(web, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        errorPanel = new LinearLayout(this);
        errorPanel.setOrientation(LinearLayout.VERTICAL);
        errorPanel.setGravity(Gravity.CENTER);
        errorPanel.setPadding(dp(24), dp(24), dp(24), dp(24));
        errorPanel.setVisibility(View.GONE);

        TextView heading = new TextView(this);
        heading.setText("Page load nahi ho paya");
        heading.setTextColor(Color.BLACK);
        heading.setTextSize(20);
        errorPanel.addView(heading);

        errorMessage = new TextView(this);
        errorMessage.setTextColor(Color.DKGRAY);
        errorMessage.setTextSize(15);
        errorMessage.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams messageParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        messageParams.topMargin = dp(12);
        errorPanel.addView(errorMessage, messageParams);

        Button retry = new Button(this);
        retry.setText("Dobara koshish karein");
        retry.setOnClickListener(v -> loadApp());
        LinearLayout.LayoutParams buttonParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        buttonParams.topMargin = dp(16);
        errorPanel.addView(retry, buttonParams);

        root.addView(errorPanel, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        setContentView(root);
    }

    private void configureWebView() {
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setJavaScriptCanOpenWindowsAutomatically(false);
        settings.setSupportMultipleWindows(false);
        settings.setLoadsImagesAutomatically(true);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);

        CookieManager cookies = CookieManager.getInstance();
        cookies.setAcceptCookie(true);
        cookies.setAccept第三方Cookies(web);

        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                progress.setProgress(newProgress);
                progress.setVisibility(newProgress >= 100 ? View.GONE : View.VISIBLE);
            }
        });

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return handleUrl(request.getUrl());
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                return handleUrl(Uri.parse(url));
            }

            @Override
            public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
                errorPanel.setVisibility(View.GONE);
                web.setVisibility(View.VISIBLE);
                progress.setVisibility(View.VISIBLE);
                progress.setProgress(0);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                progress.setVisibility(View.GONE);
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request != null && request.isForMainFrame()) {
                    String description = error == null ? "Network error" : error.getDescription().toString();
                    showError("Internet connection check karein aur phir retry karein.\n" + description);
                }
            }

            @Override
            public void onReceivedHttpError(WebView view, WebResourceRequest request,
                                            android.webkit.WebResourceResponse response) {
                if (request != null && request.isForMainFrame() && response != null
                        && response.getStatusCode() >= 400) {
                    showError("Website ne error diya (HTTP " + response.getStatusCode()
                            + "). Thodi der baad retry karein.");
                }
            }
        });
    }

    private boolean handleUrl(Uri uri) {
        String scheme = uri.getScheme();
        if ("http".equalsIgnoreCase(scheme) || "https".equalsIgnoreCase(scheme)) {
            return false;
        }

        try {
            startActivity(new Intent(Intent.ACTION_VIEW, uri));
        } catch (Exception ignored) {
            // No app on the device can handle this link.
        }
        return true;
    }

    private void loadApp() {
        if (web == null) {
            showError("WebView initialize nahi ho paya.");
            return;
        }
        errorPanel.setVisibility(View.GONE);
        web.setVisibility(View.VISIBLE);
        progress.setVisibility(View.VISIBLE);
        progress.setProgress(0);
        web.loadUrl(APP_URL);
    }

    private void showError(String message) {
        if (errorMessage != null && errorPanel != null) {
            errorMessage.setText(message);
            web.setVisibility(View.GONE);
            progress.setVisibility(View.GONE);
            errorPanel.setVisibility(View.VISIBLE);
        }
    }

    private String safeMessage(Exception exception) {
        String message = exception.getMessage();
        return message == null || message.trim().isEmpty()
                ? exception.getClass().getSimpleName() : message;
    }

    private int dp(int value) {
        return (int) (value * getResources().getDisplayMetrics().density + 0.5f);
    }

    @Override
    public void onBackPressed() {
        if (web != null && web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onDestroy() {
        if (web != null) {
            web.stopLoading();
            web.setWebChromeClient(null);
            web.setWebViewClient(null);
            web.destroy();
            web = null;
        }
        super.onDestroy();
    }
}
