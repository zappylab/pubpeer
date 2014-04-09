DROP TABLE IF EXISTS pubpeer_comments;
CREATE TABLE pubpeer_comments (
  pubpeer_comment_id int(10) unsigned NOT NULL AUTO_INCREMENT,
  article_id int(11) NOT NULL,
  doi varchar(128) NOT NULL DEFAULT '',
  comment_count int(10) unsigned NOT NULL DEFAULT '0',
  pubpeer_id varchar(32) NOT NULL DEFAULT '',
  link varchar(512) NOT NULL DEFAULT '',
  comments text,
  last_modified timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (pubpeer_comment_id),
  KEY article_id (article_id),
  KEY doi (doi,article_id),
  KEY pubpeer_id (pubpeer_id)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS pubpeer_bad_doi;
CREATE TABLE pubpeer_bad_doi (
  pubpeer_bad_doi_id int(10) unsigned NOT NULL AUTO_INCREMENT,
  doi varchar(128) NOT NULL DEFAULT '',
  last_tried timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (pubpeer_bad_doi_id)
) ENGINE=InnoDB;
