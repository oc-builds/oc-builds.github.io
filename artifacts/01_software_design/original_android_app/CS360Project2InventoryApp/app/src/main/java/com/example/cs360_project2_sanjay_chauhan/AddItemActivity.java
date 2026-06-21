package com.example.cs360_project2_sanjay_chauhan;

import android.Manifest;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.widget.Toast;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import com.google.android.material.materialswitch.MaterialSwitch;
import com.google.android.material.appbar.MaterialToolbar;

public class AddItemActivity extends AppCompatActivity {

    private static final int SMS_PERMISSION_CODE = 101;
    private MaterialSwitch smsAlertsSwitch;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_add_item);

        // back button in toolbar
        MaterialToolbar toolbar = findViewById(R.id.topAppBar);
        toolbar.setNavigationOnClickListener(v -> finish());

        // cancel goes back
        findViewById(R.id.cancel_button).setOnClickListener(v -> finish());

        // save just shows a toast for now, database writes go in Project Three
        findViewById(R.id.save_button).setOnClickListener(v -> {
            Toast.makeText(this, "Item saved", Toast.LENGTH_SHORT).show();
            finish();
        });

        // when user flips the SMS alerts toggle, check permission first
        smsAlertsSwitch = findViewById(R.id.sms_alerts_switch);
        smsAlertsSwitch.setOnCheckedChangeListener((buttonView, isChecked) -> {
            if (isChecked) {
                if (ContextCompat.checkSelfPermission(this, Manifest.permission.SEND_SMS)
                        != PackageManager.PERMISSION_GRANTED) {
                    // don't have it yet, ask the user
                    ActivityCompat.requestPermissions(this,
                            new String[]{Manifest.permission.SEND_SMS},
                            SMS_PERMISSION_CODE);
                } else {
                    Toast.makeText(this, "SMS alerts enabled", Toast.LENGTH_SHORT).show();
                }
            }
        });
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions,
                                           @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);

        if (requestCode == SMS_PERMISSION_CODE) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                Toast.makeText(this, "SMS permission granted", Toast.LENGTH_SHORT).show();
            } else {
                // denied, turn the toggle back off and let the user know
                smsAlertsSwitch.setChecked(false);
                Toast.makeText(this, "SMS permission denied. Alerts will not be sent.",
                        Toast.LENGTH_LONG).show();
            }
        }
    }
}
