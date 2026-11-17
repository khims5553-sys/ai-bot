package com.nseai.bot;

import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.TextView;

public class MainActivity extends Activity {

    private static final String APP_URL = "https://dashboardpy-fxqfhb5xeacbtk4vue38j2.streamlit.app";
    private WebView web;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);

        try {
            web = new WebView(this);
            web.setLayoutParams(new android.view.ViewGroup.LayoutParams(
                    android.view.ViewGroup.LayoutParams.MATCH_PARENT,
                    android.view.ViewGroup.LayoutParams.MATCH_PARENT));

            WebSettings s = web.getSettings();
            s.setJavaScriptEnabled(true);
            s.setDomStorageEnabled(true);
            s.setDatabaseEnabled(true);
            s.setSupportZoom(true);
            s.setBuiltInZoomControls(true);
            s.setDisplayZoomControls(false);
            s.setAllowFileAccess(false);
            s.setAllowContentAccess(false);
            s.setCacheMode(WebSettings.LOAD_DEFAULT);

            web.setWebViewClient(new WebViewClient() {
                @Override
                public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                    return false;
                }

                @Override
                public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                    if (request != null && request.isForMainFrame()) {
                        String msg = (error != null && error.getDescription() != null)
                                ? error.getDescription().toString()
                                : "Unknown network error";

                        view.loadData(
                                "<html><body style='font-family:sans-serif;padding:24px;color:#111;'>" +
                                        "<h3>Page load error</h3>" +
                                        "<p>" + msg + "</p>" +
                                        "</body></html>",
                                "text/html",
                                "UTF-8"
                        );
                    }
                }
            });

            setContentView(web);
            web.loadUrl(APP_URL);

        } catch (Throwable t) {
            TextView tv = new TextView(this);
            tv.setText("Error: " + t);
            tv.setPadding(32, 64, 32, 32);
            setContentView(tv);
        }
    }

    @Override
    public void onBackPressed() {
        if (web != null && web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
