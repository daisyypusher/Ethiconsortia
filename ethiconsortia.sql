-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: localhost
-- Generation Time: May 10, 2026 at 12:53 PM
-- Server version: 10.4.28-MariaDB
-- PHP Version: 8.2.4

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `ethiconsortia`
--

-- --------------------------------------------------------

--
-- Table structure for table `flagged_messages`
--

CREATE TABLE `flagged_messages` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `room_msg_id` int(11) DEFAULT NULL COMMENT 'NULL for private/DM messages',
  `original` text NOT NULL COMMENT 'Original message before censoring',
  `censored` text NOT NULL COMMENT 'Message after censoring',
  `flagged_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `flagged_messages`
--

INSERT INTO `flagged_messages` (`id`, `user_id`, `room_msg_id`, `original`, `censored`, `flagged_at`) VALUES
(1, 1, 2, 'Fuck', '****', '2026-05-10 09:49:57');

-- --------------------------------------------------------

--
-- Table structure for table `messages`
--

CREATE TABLE `messages` (
  `message_id` int(11) NOT NULL,
  `sender_id` int(11) NOT NULL,
  `receiver_id` int(11) NOT NULL,
  `content` text NOT NULL,
  `sent_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `is_read` tinyint(4) DEFAULT 0,
  `msg_type` varchar(10) NOT NULL DEFAULT 'text',
  `image_data` mediumtext DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `rooms`
--

CREATE TABLE `rooms` (
  `room_id` int(11) NOT NULL,
  `room_name` varchar(100) NOT NULL,
  `description` text DEFAULT '',
  `host_id` int(11) NOT NULL,
  `invite_code` varchar(20) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `rooms`
--

INSERT INTO `rooms` (`room_id`, `room_name`, `description`, `host_id`, `invite_code`, `created_at`) VALUES
(1, 'CC103', 'Intermediate Programming', 1, '87534F46', '2026-05-10 08:05:52');

-- --------------------------------------------------------

--
-- Table structure for table `room_members`
--

CREATE TABLE `room_members` (
  `member_id` int(11) NOT NULL,
  `room_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `room_role` enum('host','member') DEFAULT 'member',
  `joined_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `room_members`
--

INSERT INTO `room_members` (`member_id`, `room_id`, `user_id`, `room_role`, `joined_at`) VALUES
(1, 1, 1, 'host', '2026-05-10 08:05:52');

-- --------------------------------------------------------

--
-- Table structure for table `room_messages`
--

CREATE TABLE `room_messages` (
  `message_id` int(11) NOT NULL,
  `sub_room_id` int(11) NOT NULL,
  `sender_id` int(11) NOT NULL,
  `content` text NOT NULL,
  `sent_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `is_private` tinyint(1) NOT NULL DEFAULT 0 COMMENT '1 = private DM message',
  `receiver_id` int(11) DEFAULT NULL COMMENT 'Target user for DM messages',
  `msg_type` varchar(10) NOT NULL DEFAULT 'text'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `room_messages`
--

INSERT INTO `room_messages` (`message_id`, `sub_room_id`, `sender_id`, `content`, `sent_at`, `is_private`, `receiver_id`, `msg_type`) VALUES
(1, 3, 1, 'hello', '2026-05-10 08:06:19', 0, NULL, 'text'),
(2, 1, 1, '****', '2026-05-10 09:49:57', 0, NULL, 'text');

-- --------------------------------------------------------

--
-- Table structure for table `room_permissions`
--

CREATE TABLE `room_permissions` (
  `perm_id` int(11) NOT NULL,
  `room_id` int(11) NOT NULL,
  `target_role` enum('student','professor') NOT NULL,
  `can_send_messages` tinyint(4) DEFAULT 1,
  `can_read_history` tinyint(4) DEFAULT 1,
  `can_manage_members` tinyint(4) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `room_permissions`
--

INSERT INTO `room_permissions` (`perm_id`, `room_id`, `target_role`, `can_send_messages`, `can_read_history`, `can_manage_members`) VALUES
(1, 1, 'student', 1, 1, 1),
(2, 1, 'professor', 1, 1, 1);

-- --------------------------------------------------------

--
-- Table structure for table `room_sub_rooms`
--

CREATE TABLE `room_sub_rooms` (
  `sub_room_id` int(11) NOT NULL,
  `room_id` int(11) NOT NULL,
  `sub_room_name` varchar(50) NOT NULL,
  `sub_room_type` enum('text','announcement') DEFAULT 'text',
  `position` int(11) DEFAULT 0,
  `sub_room_type_detail` enum('public','private') NOT NULL DEFAULT 'public',
  `dm_user_a` int(11) DEFAULT NULL COMMENT 'Lower user_id of the DM pair',
  `dm_user_b` int(11) DEFAULT NULL COMMENT 'Higher user_id of the DM pair'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `room_sub_rooms`
--

INSERT INTO `room_sub_rooms` (`sub_room_id`, `room_id`, `sub_room_name`, `sub_room_type`, `position`, `sub_room_type_detail`, `dm_user_a`, `dm_user_b`) VALUES
(1, 1, 'General', 'text', 0, 'public', NULL, NULL),
(2, 1, 'Announcements', 'announcement', 1, 'public', NULL, NULL),
(3, 1, 'open-forum', 'text', 2, 'public', NULL, NULL),
(4, 1, 'hello', 'text', 3, 'public', NULL, NULL);

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `user_id` int(11) NOT NULL,
  `full_name` varchar(100) DEFAULT '',
  `username` varchar(50) NOT NULL,
  `password` varchar(255) NOT NULL,
  `role` enum('student','professor','admin') DEFAULT 'student',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`user_id`, `full_name`, `username`, `password`, `role`, `created_at`) VALUES
(1, 'Jed Igloso', 'jed', 'jed12345678', 'student', '2026-05-10 08:05:24');

-- --------------------------------------------------------

--
-- Table structure for table `verification_codes`
--

CREATE TABLE `verification_codes` (
  `code_id` int(11) NOT NULL,
  `role` varchar(20) NOT NULL,
  `code` varchar(50) NOT NULL,
  `is_active` tinyint(4) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `verification_codes`
--

INSERT INTO `verification_codes` (`code_id`, `role`, `code`, `is_active`) VALUES
(3, 'professor', 'PROF-ETHIC-2025', 1),
(4, 'admin', 'ADMIN-ETHIC-9999', 1);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `flagged_messages`
--
ALTER TABLE `flagged_messages`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`);

--
-- Indexes for table `messages`
--
ALTER TABLE `messages`
  ADD PRIMARY KEY (`message_id`),
  ADD KEY `sender_id` (`sender_id`),
  ADD KEY `receiver_id` (`receiver_id`);

--
-- Indexes for table `rooms`
--
ALTER TABLE `rooms`
  ADD PRIMARY KEY (`room_id`),
  ADD UNIQUE KEY `invite_code` (`invite_code`),
  ADD KEY `host_id` (`host_id`);

--
-- Indexes for table `room_members`
--
ALTER TABLE `room_members`
  ADD PRIMARY KEY (`member_id`),
  ADD UNIQUE KEY `uq_room_member` (`room_id`,`user_id`),
  ADD KEY `user_id` (`user_id`);

--
-- Indexes for table `room_messages`
--
ALTER TABLE `room_messages`
  ADD PRIMARY KEY (`message_id`),
  ADD KEY `channel_id` (`sub_room_id`),
  ADD KEY `sender_id` (`sender_id`);

--
-- Indexes for table `room_permissions`
--
ALTER TABLE `room_permissions`
  ADD PRIMARY KEY (`perm_id`),
  ADD UNIQUE KEY `uq_perm` (`room_id`,`target_role`);

--
-- Indexes for table `room_sub_rooms`
--
ALTER TABLE `room_sub_rooms`
  ADD PRIMARY KEY (`sub_room_id`),
  ADD KEY `room_id` (`room_id`),
  ADD KEY `idx_dm_pair` (`room_id`,`sub_room_type_detail`,`dm_user_a`,`dm_user_b`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`user_id`),
  ADD UNIQUE KEY `username` (`username`);

--


--
-- Indexes for table `verification_codes`
--
ALTER TABLE `verification_codes`
  ADD PRIMARY KEY (`code_id`),
  ADD UNIQUE KEY `code` (`code`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `flagged_messages`
--
ALTER TABLE `flagged_messages`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `messages`
--
ALTER TABLE `messages`
  MODIFY `message_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `rooms`
--
ALTER TABLE `rooms`
  MODIFY `room_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `room_members`
--
ALTER TABLE `room_members`
  MODIFY `member_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `room_messages`
--
ALTER TABLE `room_messages`
  MODIFY `message_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `room_permissions`
--
ALTER TABLE `room_permissions`
  MODIFY `perm_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT for table `room_sub_rooms`
--
ALTER TABLE `room_sub_rooms`
  MODIFY `sub_room_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `user_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `verification_codes`
--
ALTER TABLE `verification_codes`
  MODIFY `code_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `flagged_messages`
--
ALTER TABLE `flagged_messages`
  ADD CONSTRAINT `flagged_messages_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE;

--
-- Constraints for table `messages`
--
ALTER TABLE `messages`
  ADD CONSTRAINT `messages_ibfk_1` FOREIGN KEY (`sender_id`) REFERENCES `users` (`user_id`),
  ADD CONSTRAINT `messages_ibfk_2` FOREIGN KEY (`receiver_id`) REFERENCES `users` (`user_id`);

--
-- Constraints for table `rooms`
--
ALTER TABLE `rooms`
  ADD CONSTRAINT `rooms_ibfk_1` FOREIGN KEY (`host_id`) REFERENCES `users` (`user_id`);

--
-- Constraints for table `room_members`
--
ALTER TABLE `room_members`
  ADD CONSTRAINT `room_members_ibfk_1` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `room_members_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`);

--
-- Constraints for table `room_messages`
--
ALTER TABLE `room_messages`
  ADD CONSTRAINT `room_messages_ibfk_1` FOREIGN KEY (`sub_room_id`) REFERENCES `room_sub_rooms` (`sub_room_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `room_messages_ibfk_2` FOREIGN KEY (`sender_id`) REFERENCES `users` (`user_id`);

--
-- Constraints for table `room_permissions`
--
ALTER TABLE `room_permissions`
  ADD CONSTRAINT `room_permissions_ibfk_1` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`) ON DELETE CASCADE;

--
-- Constraints for table `room_sub_rooms`
--
ALTER TABLE `room_sub_rooms`
  ADD CONSTRAINT `room_sub_rooms_ibfk_1` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`) ON DELETE CASCADE;

-- ═══════════ Ethiconsortia schema sync ═══════════

-- rooms: nullable host, department + archive columns
ALTER TABLE `rooms` DROP FOREIGN KEY `rooms_ibfk_1`;
ALTER TABLE `rooms`
  MODIFY `host_id` int(11) DEFAULT NULL,
  ADD COLUMN `department_id` varchar(50) DEFAULT NULL,
  ADD COLUMN `department_name` varchar(100) DEFAULT NULL,
  ADD COLUMN `is_archived` tinyint(1) NOT NULL DEFAULT 0,
  ADD COLUMN `archived_at` timestamp NULL DEFAULT NULL,
  ADD KEY `idx_rooms_department` (`department_id`);
ALTER TABLE `rooms`
  ADD CONSTRAINT `rooms_ibfk_1` FOREIGN KEY (`host_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL;

-- room_members: per-member permissions
ALTER TABLE `room_members`
  ADD COLUMN `can_send_messages` tinyint(1) NOT NULL DEFAULT 1,
  ADD COLUMN `can_read_history` tinyint(1) NOT NULL DEFAULT 1,
  ADD COLUMN `can_manage_members` tinyint(1) NOT NULL DEFAULT 0,
  ADD COLUMN `can_post_announcements` tinyint(1) NOT NULL DEFAULT 0;
UPDATE `room_members` SET `can_manage_members` = 1 WHERE `room_role` = 'host';

-- room_messages: longtext for attachments, edit/tag/read columns
ALTER TABLE `room_messages`
  MODIFY `content` longtext NOT NULL,
  ADD COLUMN `is_edited` tinyint(1) NOT NULL DEFAULT 0,
  ADD COLUMN `edited_at` timestamp NULL DEFAULT NULL,
  ADD COLUMN `msg_tag` varchar(20) NOT NULL DEFAULT 'none',
  ADD COLUMN `msg_tag_label` varchar(20) DEFAULT NULL,
  ADD COLUMN `receiver_read` tinyint(1) NOT NULL DEFAULT 0;
UPDATE `room_messages` SET `receiver_read` = 1;   -- everything that already exists counts as read
ALTER TABLE `room_messages`
  ADD CONSTRAINT `room_messages_ibfk_3` FOREIGN KEY (`receiver_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL;

-- room_sub_rooms: "Everyone" permissions
ALTER TABLE `room_sub_rooms`
  ADD COLUMN `everyone_read` tinyint(1) NOT NULL DEFAULT 1,
  ADD COLUMN `everyone_send` tinyint(1) NOT NULL DEFAULT 1,
  ADD COLUMN `everyone_upload` tinyint(1) NOT NULL DEFAULT 1;
UPDATE `room_sub_rooms` SET `everyone_send` = 0, `everyone_upload` = 0
  WHERE `sub_room_type` = 'announcement';

-- flagged_messages: category + sub-room (backfilled from the message when possible)
ALTER TABLE `flagged_messages`
  ADD COLUMN `category` varchar(20) NOT NULL DEFAULT 'filtered',
  ADD COLUMN `sub_room_id` int(11) DEFAULT NULL;
UPDATE `flagged_messages` fm
  JOIN `room_messages` m ON m.`message_id` = fm.`room_msg_id`
  SET fm.`sub_room_id` = m.`sub_room_id`
  WHERE fm.`sub_room_id` IS NULL;
ALTER TABLE `flagged_messages`
  ADD CONSTRAINT `flagged_messages_ibfk_2` FOREIGN KEY (`sub_room_id`) REFERENCES `room_sub_rooms` (`sub_room_id`) ON DELETE CASCADE;

-- ── new tables ──
CREATE TABLE `message_edits` (
  `edit_id` int(11) NOT NULL AUTO_INCREMENT,
  `message_id` int(11) NOT NULL,
  `old_content` longtext NOT NULL,
  `new_content` longtext NOT NULL,
  `edited_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`edit_id`),
  KEY `idx_edits_message` (`message_id`),
  CONSTRAINT `message_edits_ibfk_1` FOREIGN KEY (`message_id`) REFERENCES `room_messages` (`message_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `flagged_reads` (
  `flag_id` int(11) NOT NULL,
  `admin_id` int(11) NOT NULL,
  `read_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`flag_id`,`admin_id`),
  CONSTRAINT `flagged_reads_ibfk_1` FOREIGN KEY (`flag_id`) REFERENCES `flagged_messages` (`id`) ON DELETE CASCADE,
  CONSTRAINT `flagged_reads_ibfk_2` FOREIGN KEY (`admin_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `filtered_words` (
  `word_id` int(11) NOT NULL AUTO_INCREMENT,
  `room_id` int(11) DEFAULT NULL COMMENT 'NULL = applies to all rooms',
  `word` varchar(50) NOT NULL,
  `added_by` int(11) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`word_id`),
  KEY `idx_fw_room` (`room_id`),
  CONSTRAINT `filtered_words_ibfk_1` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`) ON DELETE CASCADE,
  CONSTRAINT `filtered_words_ibfk_2` FOREIGN KEY (`added_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `room_warnings` (
  `user_id` int(11) NOT NULL,
  `room_id` int(11) NOT NULL,
  `warn_count` int(11) NOT NULL DEFAULT 0,
  PRIMARY KEY (`user_id`,`room_id`),
  CONSTRAINT `room_warnings_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `room_warnings_ibfk_2` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `room_bans` (
  `ban_id` int(11) NOT NULL AUTO_INCREMENT,
  `room_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `banned_by` int(11) DEFAULT NULL,
  `banned_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`ban_id`),
  UNIQUE KEY `uq_room_ban` (`room_id`,`user_id`),
  CONSTRAINT `room_bans_ibfk_1` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`) ON DELETE CASCADE,
  CONSTRAINT `room_bans_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `room_bans_ibfk_3` FOREIGN KEY (`banned_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `department_bans` (
  `ban_id` int(11) NOT NULL AUTO_INCREMENT,
  `department_id` varchar(50) NOT NULL,
  `user_id` int(11) NOT NULL,
  `banned_by` int(11) DEFAULT NULL,
  `banned_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`ban_id`),
  UNIQUE KEY `uq_dept_ban` (`department_id`,`user_id`),
  CONSTRAINT `department_bans_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `department_bans_ibfk_2` FOREIGN KEY (`banned_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `admin_departments` (
  `user_id` int(11) NOT NULL,
  `department_id` varchar(50) NOT NULL,
  PRIMARY KEY (`user_id`,`department_id`),
  CONSTRAINT `admin_departments_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `room_roles` (
  `role_id` int(11) NOT NULL AUTO_INCREMENT,
  `room_id` int(11) NOT NULL,
  `role_name` varchar(30) NOT NULL,
  PRIMARY KEY (`role_id`),
  UNIQUE KEY `uq_role_name` (`room_id`,`role_name`),
  CONSTRAINT `room_roles_ibfk_1` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `room_member_roles` (
  `room_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `role_id` int(11) NOT NULL,
  PRIMARY KEY (`role_id`,`user_id`),
  KEY `idx_mr_room_user` (`room_id`,`user_id`),
  CONSTRAINT `room_member_roles_ibfk_1` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`) ON DELETE CASCADE,
  CONSTRAINT `room_member_roles_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `room_member_roles_ibfk_3` FOREIGN KEY (`role_id`) REFERENCES `room_roles` (`role_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `sub_room_role_perms` (
  `sub_room_id` int(11) NOT NULL,
  `role_id` int(11) NOT NULL,
  `can_read` tinyint(1) NOT NULL DEFAULT 0,
  `can_send` tinyint(1) NOT NULL DEFAULT 0,
  `can_upload` tinyint(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`sub_room_id`,`role_id`),
  CONSTRAINT `sub_room_role_perms_ibfk_1` FOREIGN KEY (`sub_room_id`) REFERENCES `room_sub_rooms` (`sub_room_id`) ON DELETE CASCADE,
  CONSTRAINT `sub_room_role_perms_ibfk_2` FOREIGN KEY (`role_id`) REFERENCES `room_roles` (`role_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
