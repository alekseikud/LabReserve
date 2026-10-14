-- Pending requests reserve a slot too. Adjacent intervals are allowed.
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE reservations_reservation ADD CONSTRAINT reservation_no_overlap
    EXCLUDE USING gist (
        equipment_id WITH =,
        tstzrange(starts_at, ends_at, '[)') WITH &&
    ) WHERE (status IN ('pending', 'approved'));
