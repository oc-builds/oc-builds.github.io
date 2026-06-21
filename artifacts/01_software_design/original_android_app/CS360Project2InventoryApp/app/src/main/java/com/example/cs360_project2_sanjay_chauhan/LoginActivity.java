package com.example.cs360_project2_sanjay_chauhan;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import com.google.android.material.button.MaterialButton;
import com.google.android.material.textfield.TextInputEditText;

public class LoginActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_login);

        TextInputEditText usernameInput = findViewById(R.id.username_input);
        TextInputEditText passwordInput = findViewById(R.id.password_input);
        TextView errorMessage = findViewById(R.id.error_message);
        MaterialButton loginButton = findViewById(R.id.login_button);
        MaterialButton createAccountButton = findViewById(R.id.create_account_button);

        // disable login until user types something
        loginButton.setEnabled(false);

        // enable login button when both fields have text
        android.text.TextWatcher watcher = new android.text.TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}

            @Override
            public void onTextChanged(CharSequence s, int start, int before, int count) {
                String user = usernameInput.getText() != null ? usernameInput.getText().toString() : "";
                String pass = passwordInput.getText() != null ? passwordInput.getText().toString() : "";
                loginButton.setEnabled(!user.isEmpty() && !pass.isEmpty());
            }

            @Override
            public void afterTextChanged(android.text.Editable s) {}
        };
        usernameInput.addTextChangedListener(watcher);
        passwordInput.addTextChangedListener(watcher);

        loginButton.setOnClickListener(v -> {
            String username = usernameInput.getText() != null ? usernameInput.getText().toString().trim() : "";
            String password = passwordInput.getText() != null ? passwordInput.getText().toString().trim() : "";

            if (username.isEmpty() || password.isEmpty()) {
                errorMessage.setText(R.string.login_error_empty);
                errorMessage.setVisibility(View.VISIBLE);
                return;
            }

            // credential check goes here once the database is set up
            errorMessage.setVisibility(View.GONE);
            Intent intent = new Intent(LoginActivity.this, InventoryActivity.class);
            startActivity(intent);
        });

        createAccountButton.setOnClickListener(v -> {
            String username = usernameInput.getText() != null ? usernameInput.getText().toString().trim() : "";
            String password = passwordInput.getText() != null ? passwordInput.getText().toString().trim() : "";

            if (username.isEmpty() || password.isEmpty()) {
                errorMessage.setText(R.string.login_error_empty);
                errorMessage.setVisibility(View.VISIBLE);
                return;
            }

            // insert new user once the database is set up
            errorMessage.setVisibility(View.GONE);
            Intent intent = new Intent(LoginActivity.this, InventoryActivity.class);
            startActivity(intent);
        });
    }
}
