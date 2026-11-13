package org.earthsystem.trenddetective;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.ViewGroup;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

public class MainActivity extends Activity {
    private static final int PICK_REPORT = 42;
    private LinearLayout root;
    private WebView webView;
    private TextView hint;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(Color.rgb(13, 28, 48));
        getWindow().setNavigationBarColor(Color.rgb(13, 28, 48));
        buildScreen();
    }

    private void buildScreen() {
        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.rgb(245, 248, 252));
        root.setPadding(dp(18), dp(22), dp(18), dp(12));

        TextView title = new TextView(this);
        title.setText("Earth System\nTrend Detective");
        title.setTextColor(Color.rgb(15, 35, 58));
        title.setTextSize(25);
        title.setGravity(Gravity.CENTER_VERTICAL);
        title.setTypeface(null, 1);
        root.addView(title, new LinearLayout.LayoutParams(-1, -2));

        TextView subtitle = new TextView(this);
        subtitle.setText("Просмотр научного отчёта NASA на телефоне\nОткрывает сохранённый HTML и работает офлайн.");
        subtitle.setTextColor(Color.rgb(70, 85, 102));
        subtitle.setTextSize(14);
        subtitle.setPadding(0, dp(10), 0, dp(16));
        root.addView(subtitle);

        Button open = new Button(this);
        open.setText("ОТКРЫТЬ ОТЧЁТ report.html");
        open.setAllCaps(false);
        open.setOnClickListener(v -> chooseReport());
        root.addView(open, new LinearLayout.LayoutParams(-1, -2));

        hint = new TextView(this);
        hint.setText("Выберите report.html, созданный основной программой или скачанный из GitHub Actions.");
        hint.setTextColor(Color.rgb(85, 100, 116));
        hint.setTextSize(13);
        hint.setPadding(0, dp(12), 0, dp(8));
        root.addView(hint);

        webView = new WebView(this);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        webView.setBackgroundColor(Color.WHITE);
        root.addView(webView, new LinearLayout.LayoutParams(-1, 0, 1));

        setContentView(root);
    }

    private void chooseReport() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("text/html");
        startActivityForResult(intent, PICK_REPORT);
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != PICK_REPORT || resultCode != RESULT_OK || data == null) return;
        Uri uri = data.getData();
        if (uri == null) return;
        try (InputStream input = getContentResolver().openInputStream(uri);
             ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            if (input == null) throw new IllegalStateException("Файл недоступен");
            byte[] buffer = new byte[8192];
            int count;
            while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
            String html = new String(output.toByteArray(), StandardCharsets.UTF_8);
            if (!html.toLowerCase().contains("<html") && !html.toLowerCase().contains("<!doctype")) {
                throw new IllegalArgumentException("Выбранный файл не похож на HTML-отчёт");
            }
            webView.loadDataWithBaseURL("https://offline-report.invalid/", html, "text/html", "UTF-8", null);
            hint.setText("Отчёт загружен. Для просмотра повторно интернет не требуется.");
        } catch (Exception error) {
            Toast.makeText(this, "Не удалось открыть отчёт: " + error.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    private int dp(int value) {
        return (int) (value * getResources().getDisplayMetrics().density + 0.5f);
    }
}
