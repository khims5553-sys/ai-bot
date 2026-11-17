package com.nseai.bot;

import android.app.Activity;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
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
    private WebView webView;
    private LinearLayout rootLayout;
    private ProgressBar progressBar;
    private LinearLayout errorLayout;
    private TextView errorText;
    private Button retryButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        rootLayout = new LinearLayout(this);
        rootLayout.setOrientation(LinearLayout.VERTICAL);
        rootLayout.setLayoutParams(new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
        ));

        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setIndeterminate(true);
        progressBar.setVisibility(View.VISIBLE);
        LinearLayout.LayoutParams progressParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                8
        );
        rootLayout.addView(progressBar, progressParams);

        webView = new WebView(this);
        webView.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
        ));

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setSupportZoom(true);
        settings.setBuiltInZoomControls(true);
        settings.setDisplayZoomControls(false);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return false;
            }

            @Override
            public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
                super.onPageStarted(view, url, favicon);
                if (progressBar != null) {
                    progressBar.setVisibility(View.VISIBLE);
                }
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                if (progressBar != null) {
                    progressBar.setVisibility(View.GONE);
                }
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request != null && request.isForMainFrame()) {
                    String msg = (error != null && error.getDescription() != null)
                            ? error.getDescription().toString()
                            : "Network or loading error";
                    showErrorScreen("Page failed to load", msg);
                }
            }

            @Override
            public void onReceivedHttpError(WebView view, WebResourceRequest request, android.webkit.WebResourceResponse errorResponse) {
                if (request != null && request.isForMainFrame()) {
                    String msg = "HTTP error while loading page";
                    if (errorResponse != null) {
                        msg += " (" + errorResponse.getStatusCode() + ")";
                    }
                    showErrorScreen("Server error", msg);
                }
            }

            @Override
            public void onReceivedSslError(WebView view, android.webkit.SslErrorHandler handler, android.net.http.SslError error) {
                showErrorScreen("SSL certificate error", "Secure connection failed. Please try again.");
                handler.cancel();
            }
        });

        rootLayout.addView(webView);

        setContentView(rootLayout);
        loadApp();
    }

    private void loadApp() {
        try {
            if (webView != null) {
                webView.loadUrl(APP_URL);
            }
        } catch (Exception e) {
            showErrorScreen("App crash", "Unable to load app: " + e.getMessage());
        }
    }

    private void showErrorScreen(String title, String message) {
        runOnUiThread(() -> {
            if (webView != null && webView.getParent() != null) {
                ((ViewGroup) webView.getParent()).removeView(webView);
            }

            if (errorLayout == null) {
                errorLayout = new LinearLayout(this);
                errorLayout.setOrientation(LinearLayout.VERTICAL);
                errorLayout.setPadding(32, 64, 32, 64);
                errorLayout.setBackgroundColor(0xFF111827);

                TextView titleText = new TextView(this);
                titleText.setTextSize(28);
                titleText.setTextColor(0xFFFFFFFF);
                titleText.setPadding(0, 0, 0, 16);

                errorText = new TextView(this);
                errorText.setTextSize(18);
                errorText.setTextColor(0xFFFFFFFF);

                retryButton = new Button(this);
                retryButton.setText("Retry");
                retryButton.setTextSize(18);
                retryButton.setOnClickListener(v -> {
                    if (errorLayout.getParent() != null) {
                        ((ViewGroup) errorLayout.getParent()).removeView(errorLayout);
                    }
                    rootLayout.addView(webView);
                    loadApp();
                });

                errorLayout.addView(titleText);
                errorLayout.addView(errorText);
                errorLayout.addView(retryButton);
            }

            TextView titleView = (TextView) errorLayout.getChildAt(0);
            titleView.setText(title);

            errorText.setText(message);

            if (errorLayout.getParent() == null) {
                rootLayout.addView(errorLayout);
            }
        });
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
