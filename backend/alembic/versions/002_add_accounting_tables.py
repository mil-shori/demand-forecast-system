"""Add accounting tables (freee integration)

Revision ID: 002
Revises: 001
Create Date: 2026-06-10 00:00:00.000000

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create freee_tokens table
    op.create_table(
        "freee_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("company_name", sa.String(length=200), nullable=True),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("token_type", sa.String(length=20), nullable=True),
        sa.Column("scope", sa.String(length=500), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_freee_tokens_company_id"), "freee_tokens", ["company_id"], unique=True
    )
    op.create_index(
        op.f("ix_freee_tokens_is_active"), "freee_tokens", ["is_active"], unique=False
    )

    # Create account_item_mappings table
    op.create_table(
        "account_item_mappings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "mapping_type",
            sa.Enum("SALES_CATEGORY", "EXPENSE_CATEGORY", name="mappingtype"),
            nullable=False,
        ),
        sa.Column("source_key", sa.String(length=100), nullable=False),
        sa.Column("keywords", sa.Text(), nullable=True),
        sa.Column("freee_account_item_id", sa.Integer(), nullable=False),
        sa.Column("freee_account_item_name", sa.String(length=200), nullable=True),
        sa.Column("freee_tax_code", sa.Integer(), nullable=True),
        sa.Column("freee_partner_id", sa.Integer(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "mapping_type", "source_key", name="uq_account_item_mappings_type_key"
        ),
    )
    op.create_index(
        op.f("ix_account_item_mappings_mapping_type"),
        "account_item_mappings",
        ["mapping_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_account_item_mappings_active"),
        "account_item_mappings",
        ["active"],
        unique=False,
    )

    # Create journal_entries table
    op.create_table(
        "journal_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column(
            "entry_type",
            sa.Enum("SALES", "EXPENSE", name="journalentrytype"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("source_key", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("freee_company_id", sa.Integer(), nullable=True),
        sa.Column("freee_deal_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING", "SYNCED", "FAILED", "SKIPPED", name="journalentrystatus"
            ),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_type", "source_key", name="uq_journal_entries_source"
        ),
    )
    op.create_index(
        op.f("ix_journal_entries_entry_date"),
        "journal_entries",
        ["entry_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_journal_entries_entry_type"),
        "journal_entries",
        ["entry_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_journal_entries_freee_deal_id"),
        "journal_entries",
        ["freee_deal_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_journal_entries_status"), "journal_entries", ["status"], unique=False
    )
    op.create_index(
        "ix_journal_entries_date_status",
        "journal_entries",
        ["entry_date", "status"],
        unique=False,
    )

    # Create expenses table
    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("payment_method", sa.String(length=30), nullable=True),
        sa.Column("partner_name", sa.String(length=200), nullable=True),
        sa.Column("receipt_filename", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "CONFIRMED", "SYNCED", "FAILED", name="expensestatus"),
            nullable=False,
        ),
        sa.Column("freee_deal_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_expenses_expense_date"), "expenses", ["expense_date"], unique=False
    )
    op.create_index(
        op.f("ix_expenses_category"), "expenses", ["category"], unique=False
    )
    op.create_index(op.f("ix_expenses_status"), "expenses", ["status"], unique=False)
    op.create_index(
        "ix_expenses_date_status", "expenses", ["expense_date", "status"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_expenses_date_status", table_name="expenses")
    op.drop_index(op.f("ix_expenses_status"), table_name="expenses")
    op.drop_index(op.f("ix_expenses_category"), table_name="expenses")
    op.drop_index(op.f("ix_expenses_expense_date"), table_name="expenses")
    op.drop_table("expenses")

    op.drop_index("ix_journal_entries_date_status", table_name="journal_entries")
    op.drop_index(op.f("ix_journal_entries_status"), table_name="journal_entries")
    op.drop_index(
        op.f("ix_journal_entries_freee_deal_id"), table_name="journal_entries"
    )
    op.drop_index(op.f("ix_journal_entries_entry_type"), table_name="journal_entries")
    op.drop_index(op.f("ix_journal_entries_entry_date"), table_name="journal_entries")
    op.drop_table("journal_entries")

    op.drop_index(
        op.f("ix_account_item_mappings_active"), table_name="account_item_mappings"
    )
    op.drop_index(
        op.f("ix_account_item_mappings_mapping_type"),
        table_name="account_item_mappings",
    )
    op.drop_table("account_item_mappings")

    op.drop_index(op.f("ix_freee_tokens_is_active"), table_name="freee_tokens")
    op.drop_index(op.f("ix_freee_tokens_company_id"), table_name="freee_tokens")
    op.drop_table("freee_tokens")

    sa.Enum(name="expensestatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="journalentrystatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="journalentrytype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="mappingtype").drop(op.get_bind(), checkfirst=True)
