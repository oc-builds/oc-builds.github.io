package com.example.cs360_project2_sanjay_chauhan;

import android.content.Intent;
import android.os.Bundle;
import androidx.appcompat.app.AppCompatActivity;
import com.google.android.material.floatingactionbutton.FloatingActionButton;
import com.google.android.material.button.MaterialButton;

public class InventoryActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_inventory);

        // FAB opens the add item screen
        FloatingActionButton fab = findViewById(R.id.fab_add_item);
        fab.setOnClickListener(v -> {
            Intent intent = new Intent(InventoryActivity.this, AddItemActivity.class);
            startActivity(intent);
        });

        // logout goes back to login
        MaterialButton logoutButton = findViewById(R.id.logout_button);
        logoutButton.setOnClickListener(v -> {
            Intent intent = new Intent(InventoryActivity.this, LoginActivity.class);
            intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
            startActivity(intent);
        });
    }
}
