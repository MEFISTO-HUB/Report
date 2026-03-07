from __future__ import annotations

from textwrap import dedent


def password_policy_query(server: str) -> str:
    return dedent(
        f"""
        Import-Module ActiveDirectory
        $policy = Get-ADDefaultDomainPasswordPolicy -Server '{server}'
        $policy | Select-Object MinimumPasswordLength,PasswordHistoryCount,ComplexityEnabled,LockoutThreshold,LockoutDuration,LockoutObservationWindow,MaxPasswordAge,MinPasswordAge,ReversibleEncryptionEnabled |
        ConvertTo-Json -Depth 4
        """
    )


def users_query(server: str) -> str:
    return dedent(
        f"""
        Import-Module ActiveDirectory
        Get-ADUser -Server '{server}' -Filter * -Properties DisplayName,Enabled,Department,Title,CanonicalName,MemberOf,PasswordLastSet,LastLogonDate,PasswordNeverExpires,CannotChangePassword,PasswordExpired,SmartcardLogonRequired,AccountExpirationDate,WhenCreated,adminCount |
        Select-Object SamAccountName,Name,DisplayName,Enabled,Department,Title,CanonicalName,MemberOf,PasswordLastSet,
            @{{Name='DaysSincePasswordChange';Expression={{ if ($_.PasswordLastSet) {{ ((Get-Date) - $_.PasswordLastSet).Days }} else {{ $null }} }} }},
            LastLogonDate,
            @{{Name='DaysSinceLastLogon';Expression={{ if ($_.LastLogonDate) {{ ((Get-Date) - $_.LastLogonDate).Days }} else {{ $null }} }} }},
            PasswordNeverExpires,CannotChangePassword,PasswordExpired,SmartcardLogonRequired,AccountExpirationDate,WhenCreated,adminCount |
        ConvertTo-Json -Depth 6
        """
    )


def computers_query(server: str) -> str:
    return dedent(
        f"""
        Import-Module ActiveDirectory
        Get-ADComputer -Server '{server}' -Filter * -Properties DNSHostName,OperatingSystem,OperatingSystemVersion,DistinguishedName,CanonicalName,Enabled,LastLogonDate,WhenCreated,PasswordLastSet,IPv4Address,Description |
        Select-Object Name,DNSHostName,OperatingSystem,OperatingSystemVersion,DistinguishedName,CanonicalName,Enabled,LastLogonDate,
            @{{Name='DaysSinceLastLogon';Expression={{ if ($_.LastLogonDate) {{ ((Get-Date) - $_.LastLogonDate).Days }} else {{ $null }} }} }},
            WhenCreated,PasswordLastSet,IPv4Address,Description |
        ConvertTo-Json -Depth 5
        """
    )
