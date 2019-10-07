CREATE TABLE IF NOT EXISTS story_hashes (hash VARCHAR(64) UNIQUE, locked BOOLEAN, processed BOOLEAN, created DATETIME DEFAULT CURRENT_TIMESTAMP, modified DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP) CHARACTER SET utf8;