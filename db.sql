-- 1. Users Table
CREATE TABLE Users (
    user_id SERIAL PRIMARY KEY,
    role VARCHAR(50) NOT NULL, -- e.g., 'Lessee', 'Lessor', 'Administrator'
    encrypted_credentials VARCHAR(255) NOT NULL,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    contact_details VARCHAR(255) NOT NULL,
    personal_bio TEXT,
    verification_status VARCHAR(50) DEFAULT 'Pending',
    location_preferences TEXT,
    account_status VARCHAR(50) DEFAULT 'Active'
);

-- 2. Listings Table
CREATE TABLE Listings (
    listing_id SERIAL PRIMARY KEY,
    lessor_id INT NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    rental_rate_hourly NUMERIC(10, 2),
    rental_rate_daily NUMERIC(10, 2),
    rental_rate_weekly NUMERIC(10, 2),
    seasonal_pricing_tiers JSONB, -- JSONB used to store dynamic seasonal arrays
    security_deposit NUMERIC(10, 2) DEFAULT 0.00,
    item_rules TEXT,
    availability_schedules JSONB, -- JSONB used to track dates/times
    geo_location VARCHAR(255),
    keywords_semantic_tags TEXT[], -- Array of strings for search tags
    status VARCHAR(50) DEFAULT 'Active' -- e.g., 'Active', 'Archived', 'Deleted', 'Pending'
);

-- 3. Images Table
CREATE TABLE Images (
    image_id SERIAL PRIMARY KEY,
    listing_id INT NOT NULL REFERENCES Listings(listing_id) ON DELETE CASCADE,
    image_file_url TEXT NOT NULL,
    is_primary_preview BOOLEAN DEFAULT FALSE
);

-- 4. Bookings Table
CREATE TABLE Bookings (
    booking_id SERIAL PRIMARY KEY,
    listing_id INT NOT NULL REFERENCES Listings(listing_id) ON DELETE RESTRICT,
    lessee_id INT NOT NULL REFERENCES Users(user_id) ON DELETE RESTRICT,
    start_period TIMESTAMP NOT NULL,
    end_period TIMESTAMP NOT NULL,
    rental_cost NUMERIC(10, 2) NOT NULL,
    deposit_held NUMERIC(10, 2) DEFAULT 0.00,
    service_fee NUMERIC(10, 2) DEFAULT 0.00,
    booking_status VARCHAR(50) DEFAULT 'Pending', -- 'Past', 'Active', 'Cancelled', 'Completed'
    lessor_condition_verified BOOLEAN DEFAULT FALSE,
    lessee_condition_verified BOOLEAN DEFAULT FALSE
);

-- 5. Payments Table
CREATE TABLE Payments (
    payment_id SERIAL PRIMARY KEY,
    booking_id INT NOT NULL REFERENCES Bookings(booking_id) ON DELETE CASCADE,
    payment_status VARCHAR(50) DEFAULT 'Pending' -- 'Pending', 'Escrowed', 'Disbursed', 'Refunded'
);

-- 6. Wishlist_Items Table
CREATE TABLE Wishlist_Items (
    wishlist_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    listing_id INT NOT NULL REFERENCES Listings(listing_id) ON DELETE CASCADE,
    UNIQUE(user_id, listing_id) -- Prevents duplicate saves of the same item
);

-- 7. Conversations Table
CREATE TABLE Conversations (
    conversation_id SERIAL PRIMARY KEY,
    listing_id INT NOT NULL REFERENCES Listings(listing_id) ON DELETE CASCADE,
    booking_id INT REFERENCES Bookings(booking_id) ON DELETE SET NULL, -- Nullable if chatting before booking
    lessor_id INT NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    lessee_id INT NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. Messages Table
CREATE TABLE Messages (
    message_id SERIAL PRIMARY KEY,
    conversation_id INT NOT NULL REFERENCES Conversations(conversation_id) ON DELETE CASCADE,
    sender_id INT NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. Notifications Table
CREATE TABLE Notifications (
    notification_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    delivery_method VARCHAR(50) NOT NULL, -- e.g., 'In-App', 'Email'
    type VARCHAR(50) NOT NULL, -- e.g., 'Booking Update', 'Payment Status', 'Deadline'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. Reviews Table
CREATE TABLE Reviews (
    review_id SERIAL PRIMARY KEY,
    reviewer_id INT NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    target_user_id INT REFERENCES Users(user_id) ON DELETE CASCADE, -- For counter-party reviews
    target_listing_id INT REFERENCES Listings(listing_id) ON DELETE CASCADE, -- For item reviews
    rating_score NUMERIC(3, 2) CHECK (rating_score >= 0 AND rating_score <= 5), -- Assuming a 5-star scale
    qualitative_review TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Ensure at least one target is provided
    CONSTRAINT check_review_target CHECK (target_user_id IS NOT NULL OR target_listing_id IS NOT NULL)
);

-- 11. Reports Table
CREATE TABLE Reports (
    report_id SERIAL PRIMARY KEY,
    reporter_id INT NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    reported_entity_id INT NOT NULL, -- Generic ID (can map to a user_id or listing_id)
    flag_reason VARCHAR(255) NOT NULL, -- 'Fraudulent', 'Damaged', 'Abusive'
    admin_resolution VARCHAR(255) DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);