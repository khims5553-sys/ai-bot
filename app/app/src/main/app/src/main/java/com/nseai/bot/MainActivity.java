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
            setContentView(web);
            WebSettings s = web.getSettings();
            s.setJavaScriptEnabled(true);
            s.setDomStorageEnabled(true);
            web.setWebViewClient(new WebViewClient() {
                @Override
                public void onReceivedError(WebView v, WebResourceRequest r, WebResourceError e) {
                    if (r.isForMainFrame()) {
                        v.loadData("<h3>Page load error</h3><p>" + e.getDescription() + "</p>",
                                "text/html", "UTF-8");
                    }
                }
            });
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
